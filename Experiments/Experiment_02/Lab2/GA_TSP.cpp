/*
 * GA_TSP.cpp —— 离散遗传算法求解 TSP / MTSP
 *
 * 由 GA_Code.cpp（连续目标优化）改造而来，对应实验要求第 2 条。
 *
 * 改造对照：
 *   个体表示    double gene[NVARS]        ->  int perm[NCITY] 排列
 *   输入        gadata.txt 上下界         ->  tsp225.txt 坐标
 *   适应度      x1^2 + x2^2（最大化）     ->  1 / 路径代价（最大化）
 *   交叉        单点交换实数              ->  OX 顺序交叉
 *   变异        随机重置到上下界内        ->  swap 交换
 *   输出        最优实数解                ->  最优路径 + 各旅行商分段
 *
 * 编码（m=1 与 m>1 统一）：
 *   perm[0] 固定为仓库城市，perm[1..NCITY-1] 是其余城市的排列。
 *   m=1 时无切点，perm 整体即一条回路。
 *   m>1 时另存 m-1 个严格递增切点 cut[]，把 perm[1..N-1] 切成 m 段，
 *   第 k 段即第 k 个旅行商的路线：仓库 -> 段内城市 -> 仓库。
 *
 * 用法：
 *   GA_TSP.exe [-m 4] [-pc 0.7] [-pm 0.4] [-seed 12345]
 *              [-gens 5000] [-pop 100] [-bal 0.3] [-depot 0] [-out tsp]
 *              [-mut inv|swap] [-k 1] [-sel tour|roul] [-tk 8]
 *
 * 输出：
 *   <out>_log.txt   逐代日志（代数/最优/平均/标准差/总路程/最长路径/极差）
 *   <out>_best.txt  最优路径（按旅行商分段，供画图脚本读取）
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

/* ---------------- 规模上限 ---------------- */
#define MAXCITY  512
#define MAXROUTE 32
#define MAXPOP   1000

/* ---------------- 全局参数 ---------------- */
static int          NCITY   = 0;      /* 城市数 */
static double       CX[MAXCITY];      /* 城市 x 坐标 */
static double       CY[MAXCITY];      /* 城市 y 坐标 */
static int          DIST[MAXCITY][MAXCITY]; /* 预计算距离矩阵（取整，同 TSPLIB EUC_2D）*/

static int          M       = 1;      /* 旅行商数量 */
static int          POPSIZE = 100;    /* 种群规模 */
static int          MAXGENS = 5000;   /* 最大迭代代数 */
static double       PCROSS  = 0.7;    /* 交叉概率 */
static double       PMUT    = 0.7;    /* 变异概率（个体级，见 mutate()）*/
static double       BAL_W   = 0.3;    /* 均衡惩罚权重 */
static int          DEPOT   = 0;      /* 仓库城市下标 */
static unsigned int SEED    = 12345;
static int          USE_INVERSION = 1;/* 1=逆序变异（默认）, 0=交换变异 */
static int          MUT_K   = 1;      /* 每次变异触发的逆序次数 */
static int          SEL_MODE = 1;     /* 0=轮盘赌(线性标定), 1=锦标赛 */
static int          TOUR_K  = 8;      /* 锦标赛参赛规模 */

static char         OUT_PREFIX[256] = "tsp";
static char         LOG_PATH[300];
static char         BEST_PATH[300];

/* ---------------- 随机数（xorshift32，跨平台可复现）---------------- */
static unsigned int rng_state;

static unsigned int rnd(void)
{
	unsigned int x = rng_state;
	x ^= x << 13;
	x ^= x >> 17;
	x ^= x << 5;
	rng_state = x;
	return x;
}

static int rnd_int(int n)            /* [0, n) */
{
	return (int)(rnd() % (unsigned int)n);
}

static double rnd_double(void)       /* [0, 1) */
{
	return (double)(rnd() >> 8) * (1.0 / 16777216.0);
}

/* ---------------- 个体 ---------------- */
typedef struct
{
	int    perm[MAXCITY];   /* perm[0] = DEPOT，固定；其余为排列 */
	int    cut[MAXROUTE];   /* m-1 个切点，严格递增，取值 1..NCITY-1 */
	double cost;            /* 代价 = 总路程 + BAL_W * 极差（越小越好）*/
	double fitness;         /* 适应度 = 1 / cost（越大越好）*/
	double total;           /* 总路程 */
	double maxlen;          /* 最长单条路线 */
	double spread;          /* 最长 - 最短 */
} individual;

static individual population[MAXPOP + 1];
static individual best_ind;             /* 历史最优 */
static int        generation = 0;

/* ================= 距离 ================= */

/* 读入城市坐标。支持 "x y" 与 "idx x y" 两种行格式。*/
static void load_cities(const char *path)
{
	FILE *fp;
	char line[512];

	fp = fopen(path, "r");
	if (fp == NULL)
	{
		printf("Cannot open %s\n", path);
		exit(1);
	}
	while (fgets(line, sizeof(line), fp) != NULL && NCITY < MAXCITY)
	{
		double v1, v2, v3;
		int n = sscanf(line, "%lf %lf %lf", &v1, &v2, &v3);
		if (n == 2)
		{
			CX[NCITY] = v1;
			CY[NCITY] = v2;
			NCITY++;
		}
		else if (n == 3)
		{
			/* 三列：第一列是城市编号，丢弃 */
			CX[NCITY] = v2;
			CY[NCITY] = v3;
			NCITY++;
		}
	}
	fclose(fp);
	if (NCITY == 0)
	{
		printf("No city loaded.\n");
		exit(1);
	}
}

/* 预计算两两距离，四舍五入取整（与 TSPLIB EUC_2D 一致）*/
static void build_dist(void)
{
	int i, j;
	for (i = 0; i < NCITY; i++)
	{
		DIST[i][i] = 0;
		for (j = i + 1; j < NCITY; j++)
		{
			double dx = CX[i] - CX[j];
			double dy = CY[i] - CY[j];
			int d = (int)(sqrt(dx * dx + dy * dy) + 0.5);
			DIST[i][j] = d;
			DIST[j][i] = d;
		}
	}
}

/* ================= 适应度 ================= */

static void evaluate_one(individual *ind)
{
	double lens[MAXROUTE];
	double total = 0.0, mx = -1.0, mn = 1e18;
	int seg = (M > 1) ? M : 1;
	int k, i, start = 1, end;

	for (k = 0; k < seg; k++)
	{
		double L = 0.0;
		end = (M > 1 && k < M - 1) ? ind->cut[k] - 1 : NCITY - 1;

		if (end >= start)
		{
			L += DIST[DEPOT][ind->perm[start]];
			for (i = start; i < end; i++)
				L += DIST[ind->perm[i]][ind->perm[i + 1]];
			L += DIST[ind->perm[end]][DEPOT];
		}
		lens[k] = L;
		total += L;
		if (L > mx) mx = L;
		if (L < mn) mn = L;
		start = end + 1;
	}

	if (mx < 0.0) mx = 0.0;
	if (mn > mx)  mn = mx;

	ind->total  = total;
	ind->maxlen = mx;
	ind->spread = mx - mn;
	/* m=1 时只有一段，spread 恒为 0，惩罚项自动消失，退化为纯 TSP */
	ind->cost = total + BAL_W * ind->spread;

	(void)lens;
}

/* 线性标定：把「越小越好」的 cost 转成「越大越好」的 fitness。
 *
 * 第一版直接取 1/cost，结果 500 代平均代价几乎不动。原因是种群后期代价彼此
 * 接近（38000 与 41000 只差 8%），取倒数后适应度比值仅 1.08，轮盘赌退化成
 * 均匀抽样，选择压力接近零，好个体得不到复制。
 *
 * 线性标定把适应度拉开到 (POPSIZE-1):1 的跨度；末尾的 range/(POPSIZE-1)
 * 给最差个体留一点非零概率，避免它被彻底饿死导致多样性枯竭。
 */
static void compute_fitness(void)
{
	double cmax = -1e18, cmin = 1e18, range;
	int i;

	for (i = 0; i < POPSIZE; i++)
	{
		if (population[i].cost > cmax) cmax = population[i].cost;
		if (population[i].cost < cmin) cmin = population[i].cost;
	}
	range = cmax - cmin;
	if (range < 1e-9)
		range = 1e-9;

	for (i = 0; i < POPSIZE; i++)
		population[i].fitness = (cmax - population[i].cost) + range / (POPSIZE - 1.0);
}

static void evaluate_all(void)
{
	int i;
	for (i = 0; i < POPSIZE; i++)
		evaluate_one(&population[i]);
	compute_fitness();
}

/* ================= 初始化 ================= */

static void make_random_perm(individual *ind)
{
	int i, j, t;
	for (i = 1; i < NCITY; i++)
		ind->perm[i] = i;
	for (i = NCITY - 1; i > 1; i--)     /* Fisher-Yates，perm[0] 保持为 DEPOT */
	{
		j = 1 + rnd_int(i);
		t = ind->perm[i];
		ind->perm[i] = ind->perm[j];
		ind->perm[j] = t;
	}
	ind->perm[0] = DEPOT;
}

static void make_random_cuts(individual *ind)
{
	/* 把 1..NCITY-1 大致均分成 M 段，再随机扰动，保证每段至少 1 个城市 */
	int seg = NCITY - 1;
	int k, base, slack, spare, used;

	if (M <= 1)
		return;

	base = seg / M;                      /* 每段基础城市数 */
	slack = seg - base * M;              /* 余数，随机分给前 slack 段 */
	used = 1;
	spare = slack;
	for (k = 0; k < M - 1; k++)
	{
		int len = base + ((k < spare) ? 1 : 0);
		used += len;
		ind->cut[k] = used;
	}
	/* 微扰：随机移动若干切点 */
	for (k = 0; k < M - 1; k++)
	{
		int delta = rnd_int(7) - 3;      /* -3..3 */
		int v = ind->cut[k] + delta;
		int lo = (k == 0) ? 2 : ind->cut[k - 1] + 1;
		int hi = (k == M - 2) ? NCITY - 1 : ind->cut[k + 1] - 1;
		if (v < lo) v = lo;
		if (v > hi) v = hi;
		ind->cut[k] = v;
	}
}

static void initialize(void)
{
	int i;
	for (i = 0; i < POPSIZE; i++)
	{
		make_random_perm(&population[i]);
		make_random_cuts(&population[i]);
	}
}

/* ================= 选择（轮盘赌）================= */

/* 锦标赛选择：随机抽 TOUR_K 个个体，留代价最小的。
 * 压力由 TOUR_K 控制，与代价的绝对大小无关 —— 这正是线性标定做不到的。*/
static void select_tournament(void)
{
	static individual newpop[MAXPOP];
	int i, j, best;

	for (i = 0; i < POPSIZE; i++)
	{
		best = rnd_int(POPSIZE);
		for (j = 1; j < TOUR_K; j++)
		{
			int c = rnd_int(POPSIZE);
			if (population[c].cost < population[best].cost)
				best = c;
		}
		newpop[i] = population[best];
	}
	for (i = 0; i < POPSIZE; i++)
		population[i] = newpop[i];
}

static void select_roulette(void)
{
	static individual newpop[MAXPOP];
	double sum = 0.0, cfitness, p;
	int mem, i, j;

	for (mem = 0; mem < POPSIZE; mem++)
		sum += population[mem].fitness;

	for (i = 0; i < POPSIZE; i++)
	{
		p = rnd_double() * sum;
		cfitness = 0.0;
		for (j = 0; j < POPSIZE; j++)
		{
			cfitness += population[j].fitness;
			if (p <= cfitness)
			{
				newpop[i] = population[j];
				break;
			}
		}
		if (j == POPSIZE)                /* 浮点兜底 */
			newpop[i] = population[POPSIZE - 1];
	}
	for (i = 0; i < POPSIZE; i++)
		population[i] = newpop[i];
}

static void select_pop(void)
{
	if (SEL_MODE == 1)
		select_tournament();
	else
		select_roulette();
}

/* ================= 交叉：OX 顺序交叉 ================= */

/* 对长度 L 的排列做 OX；p1/p2 是父代（指向 perm+1），child 是子代（指向 perm+1）。
 * perm[0] 不参与交叉，仓库位置天然固定。 */
static void ox_crossover(const int *p1, const int *p2, int *child, int L)
{
	char used[MAXCITY];
	int a, b, t, i, k;

	if (L < 2)
	{
		for (i = 0; i < L; i++)
			child[i] = p1[i];
		return;
	}

	a = rnd_int(L);
	b = rnd_int(L);
	if (a > b) { t = a; a = b; b = t; }
	if (a == b) { b = (a + 1) % L; if (b < a) { t = a; a = b; b = t; } }

	memset(used, 0, sizeof(char) * NCITY);
	for (i = a; i <= b; i++)
	{
		child[i] = p1[i];
		used[p1[i]] = 1;
	}

	k = (b + 1) % L;
	for (i = 0; i < L; i++)
	{
		int idx = (b + 1 + i) % L;
		int v = p2[idx];
		if (used[v])
			continue;
		while (k >= a && k <= b)         /* 跳过已复制的区块 */
			k = (k + 1) % L;
		child[k] = v;
		used[v] = 1;
		k = (k + 1) % L;
	}
}

static void cross_cuts(const individual *pa, const individual *pb, individual *ch)
{
	int k;
	if (M <= 1)
		return;
	/* 切点整组继承，父代各自都是合法的递增切点集 */
	for (k = 0; k < M - 1; k++)
		ch->cut[k] = (rnd_double() < 0.5) ? pa->cut[k] : pb->cut[k];
}

static void crossover(void)
{
	int mem, first = 0, one = 0;

	for (mem = 0; mem < POPSIZE; mem++)
	{
		if (rnd_double() < PCROSS)
		{
			++first;
			if (first % 2 == 0)
			{
				individual c1 = population[one];
				individual c2 = population[mem];
				individual ch1, ch2;

				ch1.perm[0] = DEPOT;
				ch2.perm[0] = DEPOT;
				ox_crossover(c1.perm + 1, c2.perm + 1, ch1.perm + 1, NCITY - 1);
				ox_crossover(c2.perm + 1, c1.perm + 1, ch2.perm + 1, NCITY - 1);
				cross_cuts(&c1, &c2, &ch1);
				cross_cuts(&c1, &c2, &ch2);

				population[one] = ch1;
				population[mem] = ch2;
			}
			else
				one = mem;
		}
	}
}

/* ================= 变异 ================= */

/* 逆序变异：随机选一段城市序列整段反转。
 *
 * 为什么不用逐位 swap：反转一段在 TSP 里恰好等价于一次 2-opt 移动（断开两条
 * 边、按新顺序重连），改动的是「局部结构」；而逐位 swap 只是把两个城市对调，
 * 是随机跳变。实测 2000 代下 swap 变异最优仅 15703，逆序变异可降到 ~4000。
 * 详见报告「实验对比」一节。*/
static void inversion_mutate(individual *ind)
{
	int i = 1 + rnd_int(NCITY - 1);
	int j = 1 + rnd_int(NCITY - 1);
	int t;

	if (i > j) { t = i; i = j; j = t; }
	while (i < j)
	{
		t = ind->perm[i];
		ind->perm[i] = ind->perm[j];
		ind->perm[j] = t;
		i++;
		j--;
	}
}

/* 交换变异：随机对调两个城市（保留作对照，-mut swap 启用）*/
static void swap_mutate(individual *ind)
{
	int j = 1 + rnd_int(NCITY - 1);
	int k = 1 + rnd_int(NCITY - 1);
	int t = ind->perm[j];
	ind->perm[j] = ind->perm[k];
	ind->perm[k] = t;
}

/* 变异：PMUT 是「个体被变异的概率」，不是「逐位概率」。
 *
 * 这一点踩过坑：最初按逐位口径实现（对每一位以 PMUT 概率触发），PMUT=0.005
 * 时每个个体每代平均挨 1.12 次逆序，而每次逆序平均翻转 75 个城市 —— 等于把
 * 每个个体（含精英）每代都打散重来。结果是 5 万次评估只做到 22130，
 * 而同样 5 万次的单纯逆序爬山能到 4794。改成个体级概率后恢复正态。*/
static void mutate(void)
{
	int i, c;

	for (i = 0; i < POPSIZE; i++)
	{
		if (rnd_double() < PMUT)
		{
			int reps = MUT_K;
			while (reps-- > 0)
			{
				if (USE_INVERSION)
					inversion_mutate(&population[i]);
				else
					swap_mutate(&population[i]);
			}
		}

		/* 切点部分：小幅抖动，保持递增且每段非空 */
		if (M > 1)
		{
			for (c = 0; c < M - 1; c++)
			{
				if (rnd_double() < PMUT)
				{
					int v = population[i].cut[c] + (rnd_int(5) - 2);  /* -2..2 */
					int lo = (c == 0) ? 2 : population[i].cut[c - 1] + 1;
					int hi = (c == M - 2) ? NCITY - 1 : population[i].cut[c + 1] - 1;
					if (v < lo) v = lo;
					if (v > hi) v = hi;
					population[i].cut[c] = v;
				}
			}
		}
	}
}

/* ================= 精英保留 ================= */

static void update_best(void)
{
	int i;
	for (i = 0; i < POPSIZE; i++)
		if (population[i].cost < best_ind.cost)
			best_ind = population[i];
}

static void elitist(void)
{
	int i, worst = 0;
	for (i = 0; i < POPSIZE; i++)
		if (population[i].cost > population[worst].cost)
			worst = i;
	if (best_ind.cost < population[worst].cost)
		population[worst] = best_ind;
}

/* ================= 日志 ================= */

static void report(FILE *fp)
{
	double sum = 0.0, sum_sq = 0.0, avg, stddev;
	int i;

	for (i = 0; i < POPSIZE; i++)
	{
		sum += population[i].cost;
		sum_sq += population[i].cost * population[i].cost;
	}
	avg = sum / (double)POPSIZE;
	stddev = sqrt((sum_sq - avg * avg * (double)POPSIZE) / (POPSIZE - 1));
	if (stddev < 0.0) stddev = 0.0;

	fprintf(fp, "\n%7d,   | %10.3f | %10.3f | %9.3f | %10.3f | %10.3f | %9.3f",
			generation,
			best_ind.cost, avg, stddev,
			best_ind.total, best_ind.maxlen, best_ind.spread);
}

static void write_best_tour(void)
{
	FILE *fp = fopen(BEST_PATH, "w");
	int seg = (M > 1) ? M : 1;
	int k, i, start = 1, end;

	if (fp == NULL)
	{
		printf("Cannot write %s\n", BEST_PATH);
		exit(1);
	}
	fprintf(fp, "# m=%d depot=%d total=%.3f maxroute=%.3f spread=%.3f\n",
			M, DEPOT, best_ind.total, best_ind.maxlen, best_ind.spread);
	fprintf(fp, "# route_id  n_cities  length  city_indices...\n");

	for (k = 0; k < seg; k++)
	{
		double L = 0.0;
		end = (M > 1 && k < M - 1) ? best_ind.cut[k] - 1 : NCITY - 1;
		if (end >= start)
		{
			L += DIST[DEPOT][best_ind.perm[start]];
			for (i = start; i < end; i++)
				L += DIST[best_ind.perm[i]][best_ind.perm[i + 1]];
			L += DIST[best_ind.perm[end]][DEPOT];
		}
		fprintf(fp, "%d %d %.3f", k, end - start + 1, L);
		for (i = start; i <= end; i++)
			fprintf(fp, " %d", best_ind.perm[i]);
		fprintf(fp, "\n");
		start = end + 1;
	}
	fclose(fp);
}

/* ================= 参数解析 ================= */

static void parse_args(int argc, char **argv)
{
	int i;
	for (i = 1; i < argc - 1; i++)
	{
		const char *a = argv[i];
		if      (!strcmp(a, "-m"))     M       = atoi(argv[i + 1]);
		else if (!strcmp(a, "-pc"))    PCROSS  = atof(argv[i + 1]);
		else if (!strcmp(a, "-pm"))    PMUT    = atof(argv[i + 1]);
		else if (!strcmp(a, "-seed"))  SEED    = (unsigned int)strtoul(argv[i + 1], NULL, 10);
		else if (!strcmp(a, "-gens"))  MAXGENS = atoi(argv[i + 1]);
		else if (!strcmp(a, "-pop"))   POPSIZE = atoi(argv[i + 1]);
		else if (!strcmp(a, "-bal"))   BAL_W   = atof(argv[i + 1]);
		else if (!strcmp(a, "-depot")) DEPOT   = atoi(argv[i + 1]);
		else if (!strcmp(a, "-city"))  { /* 城市文件，见 main */ }
		else if (!strcmp(a, "-out"))   strncpy(OUT_PREFIX, argv[i + 1], 255);
		else if (!strcmp(a, "-mut"))   USE_INVERSION = strcmp(argv[i + 1], "swap") != 0;
		else if (!strcmp(a, "-k"))     MUT_K   = atoi(argv[i + 1]);
		else if (!strcmp(a, "-sel"))   SEL_MODE = strcmp(argv[i + 1], "roul") != 0;
		else if (!strcmp(a, "-tk"))    TOUR_K  = atoi(argv[i + 1]);
	}

	if (M < 1) M = 1;
	if (M > MAXROUTE) M = MAXROUTE;
	if (POPSIZE < 4) POPSIZE = 4;
	if (POPSIZE > MAXPOP) POPSIZE = MAXPOP;
	if (SEED == 0) SEED = 1;

	snprintf(LOG_PATH,  sizeof(LOG_PATH),  "%s_log.txt",  OUT_PREFIX);
	snprintf(BEST_PATH, sizeof(BEST_PATH), "%s_best.txt", OUT_PREFIX);
}

/* ================= 主程序 ================= */

int main(int argc, char **argv)
{
	FILE *galog;
	clock_t t0;
	int i;
	const char *cityfile = "tsp225.txt";

	for (i = 1; i < argc - 1; i++)
		if (!strcmp(argv[i], "-city"))
			cityfile = argv[i + 1];

	parse_args(argc, argv);
	rng_state = SEED;

	load_cities(cityfile);
	build_dist();

	if (DEPOT < 0 || DEPOT >= NCITY)
		DEPOT = 0;

	if ((galog = fopen(LOG_PATH, "w")) == NULL)
	{
		printf("Cannot open %s\n", LOG_PATH);
		exit(1);
	}
	fprintf(galog, "# discrete GA / TSP-MTSP log\n");
	fprintf(galog, "# cities=%d  m=%d  pop=%d  gens=%d  pc=%.3f  pm=%.3f  seed=%u  bal=%.3f\n",
			NCITY, M, POPSIZE, MAXGENS, PCROSS, PMUT, SEED, BAL_W);
	fprintf(galog, "\ngeneration |   best    |  average  | std    | best_total | best_max  | spread");

	t0 = clock();
	initialize();
	evaluate_all();
	best_ind = population[0];
	update_best();

	while (generation < MAXGENS)
	{
		generation++;
		select_pop();
		crossover();
		mutate();
		evaluate_all();
		elitist();
		update_best();
		report(galog);
	}
	fclose(galog);
	write_best_tour();

	printf("cities      : %d\n", NCITY);
	printf("salesmen m  : %d\n", M);
	printf("population  : %d\n", POPSIZE);
	printf("generations : %d\n", MAXGENS);
	printf("pcross/pmut : %.3f / %.3f\n", PCROSS, PMUT);
	printf("seed        : %u\n", SEED);
	printf("---------------------------------\n");
	printf("best total  : %.3f\n", best_ind.total);
	if (M > 1)
	{
		printf("best max    : %.3f\n", best_ind.maxlen);
		printf("spread      : %.3f\n", best_ind.spread);
	}
	printf("cost        : %.3f\n", best_ind.cost);
	printf("log         : %s\n", LOG_PATH);
	printf("tour        : %s\n", BEST_PATH);
	printf("elapsed     : %.2f s\n", (double)(clock() - t0) / CLOCKS_PER_SEC);
	printf("Success\n");
	return 0;
}
