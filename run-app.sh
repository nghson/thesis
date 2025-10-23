bash run-generator.sh $1
g++ -o planner -O2 src/planner/*.cpp src/planner/xxHash/xxhash.c
bash path_action_names.sh $1

