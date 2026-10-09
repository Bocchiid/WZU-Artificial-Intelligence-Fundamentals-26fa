@echo off
chcp 65001 >nul
cd /d D:\WZU-Artificial-Intelligence-Fundamentals-26fa\Experiments\Experiment_02\Lab2
title GA-CONTINUOUS
mode con cols=92 lines=40
@echo on

g++ -O2 -o GA_Code.exe GA_Code.cpp
.\GA_Code.exe
