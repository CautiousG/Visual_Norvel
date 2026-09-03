@echo off
rem wiki-graph.cmd - build knowledge graph from [[wikilinks]] + tags
rem Usage: wiki-graph.cmd <wiki-dir> [--report]
rem Example: wiki-graph.cmd works/heroic_saga/01_source_and_script/wiki --report
rem Output: <work-root>/graph/graph.html + graph.json (open in browser)
setlocal
set SCRIPT=%~dp0graph.py
if "%~1"=="" (
  echo Usage: wiki-graph.cmd ^<wiki-dir^> [--report]
  exit /b 1
)
set WIKI=%~1
python "%SCRIPT%" --wiki "%WIKI%" %2 %3 %4 %5
