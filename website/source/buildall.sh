set -e
cd "$(dirname "$0")"
python3 build.py && python3 build_dl.py && python3 build_team.py && python3 build_pages2.py && python3 build_iris.py && python3 finish.py
