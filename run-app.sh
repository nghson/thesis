echo "Generating code"
bash run-generator.sh $1
echo "Compiling"
g++ -o planner -O2 src/planner/*.cpp src/planner/xxHash/xxhash.c
echo "Start running planner"
bash path-action-names.sh $1

