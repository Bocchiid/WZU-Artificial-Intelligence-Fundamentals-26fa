@echo off
chcp 65001 >nul
cd /d D:\WZU-Artificial-Intelligence-Fundamentals-26fa\Experiments\Experiment_02\Lab2
title GA-MTSP
mode con cols=92 lines=40
@echo on

.\GA_TSP.exe -m 4 -seed 1001 -out results/mtsp_m4
