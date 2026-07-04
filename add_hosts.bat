@echo off
echo 正在添加域名映射...
echo 127.0.0.1 youzizhijia.local >> %SystemRoot%\System32\drivers\etc\hosts
echo 完成！现在可以用 http://youzizhijia.local:5000/ 访问了
pause
