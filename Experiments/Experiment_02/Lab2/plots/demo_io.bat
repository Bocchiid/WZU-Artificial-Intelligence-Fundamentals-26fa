@echo off
chcp 65001 >nul
cd /d D:\WZU-Artificial-Intelligence-Fundamentals-26fa\Experiments\Experiment_02\Lab2
title GA-IO
mode con cols=100 lines=28
@echo on

powershell -NoProfile -ExecutionPolicy Bypass -File plots\show_io.ps1
