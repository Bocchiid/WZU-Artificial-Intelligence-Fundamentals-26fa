@echo off
chcp 65001 >nul
cd /d D:\WZU-Artificial-Intelligence-Fundamentals-26fa\Experiments\Experiment_02\Lab2
title GA-TSP
mode con cols=92 lines=40
@echo on

g++ -O2 -o GA_TSP.exe GA_TSP.cpp
.\GA_TSP.exe -m 1 -seed 1001 -out results/tsp_m1
