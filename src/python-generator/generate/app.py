#!/usr/bin/env python3

import concurrent.futures
import sys

from generate import parse, helpers, generator, representations, ff_generator


def main():
    if len(sys.argv) > 1:
        FILE_NAME = sys.argv[1]
    else:
        print("Missing sas file argument.")
        return
    try:
        lines = helpers.get_lines(FILE_NAME)
        root_task = parse.RootTask(lines)
    except Exception:
        print("Error reading sas file")
        return

    var_infos = representations.get_var_infos(root_task)
    assert (len(var_infos) == root_task.get_num_variables())
    ff_var_infos = ff_generator.get_ff_var_infos(root_task)
    assert (len(ff_var_infos) == root_task.get_num_variables())

    generator.write_configs(var_infos)
    ff_generator.write_ff_configs(root_task, ff_var_infos)

    with concurrent.futures.ProcessPoolExecutor(max_workers=2) as executor:
        executor.submit(generator.write_actions, root_task, var_infos)
        executor.submit(ff_generator.write_ff_graph, root_task, var_infos, ff_var_infos)


if __name__ == "__main__":
    sys.exit(main())
