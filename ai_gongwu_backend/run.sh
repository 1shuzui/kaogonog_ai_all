#!/bin/bash
# 这个脚本用最简单的方式启动旧后端；保留它是为了回归和临时排查时不用记 uvicorn 参数。
# @param: 无；依赖当前目录和已安装的 Python/FastAPI 环境。
# @return: 启动 uvicorn 开发服务，进程退出码由 uvicorn 决定。
# @raises: 当依赖缺失、端口占用或应用导入失败时由 shell/uvicorn 返回错误。
uvicorn app.main:app --reload
