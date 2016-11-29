#!/usr/bin/env python

import os
import shutil
import argparse
import subprocess

from itertools import groupby
from collections import defaultdict
from cloudscope.utils.timez import humanizedelta
from cloudscope.utils.statistics import OnlineVariance
from cloudscope.simulation.outages import OutagesReader, ONLINE, OUTAGE


SCOPE = ['python', '/Users/benjamin/Repos/umd/cloudscope/scope.py',]

SCOPE_O = SCOPE + ['outages', "-p", "global", "-t" "4320000"]
SCOPE_O += ["-M", "120000", "-S" "128", "-m" "80000", "-s", "128"]


def count_outages(path):
    clock  = 0
    deltas = defaultdict(OnlineVariance)
    reader = OutagesReader(path)

    for (ts, state), events in groupby(reader, lambda e: (e.timestep, e.state)):
        duration = ts - clock
        deltas[ONLINE if state == OUTAGE else OUTAGE].update(duration)
        clock = ts

    for key, stats in sorted(deltas.items(), key=lambda item: item[0]):
        print "{}: {:0.0f} {} events averaging {}".format(os.path.basename(path), stats.samples, key, humanizedelta(milliseconds=stats.mean))
    print

def make_outages(num, dst, topo):
    dst = os.path.join(dst, "outages")
    if not os.path.exists(dst):
        os.mkdir(dst)

    step = round(1.0 / float(num-1), 3)

    for idx in xrange(0, num):
        outpath = os.path.join(dst, "outages-{:0>2}.tsv".format(idx+1))
        prob = round(idx * step, 2)

        if prob == 0.0:
            with open(outpath, 'w') as f:
                f.write("")

        else:
            with open(os.devnull, 'w') as FNULL:
                subprocess.call(SCOPE_O + ["-w", outpath, "-o", "{:0.2f}".format(prob), topo], stdout=FNULL, stderr=subprocess.STDOUT)
            count_outages(outpath)

        yield outpath, prob


def make_experiments(args):

    dst_dir = args.dst_dir
    outages = make_outages(args.outages, dst_dir, args.topologies[0])


    for idx in xrange(1, args.outages+1):

        # Create the outage for this set of experiments.
        outage_trace, outage_prob = next(outages)


        for topo in args.topologies:
            # Copy the topology
            name, ext = os.path.splitext(os.path.basename(topo))
            dst = os.path.join(dst_dir, "{}-{:0>2}{}".format(name, idx, ext))
            shutil.copy(topo, dst)

            with open(os.devnull, 'w') as FNULL:
                subprocess.call(SCOPE + ["modify", "-M", "outages={}".format(outage_trace), dst], stdout=FNULL, stderr=subprocess.STDOUT)
                subprocess.call(SCOPE + ["modify", "-M", "outage_prob={:0.2f}".format(outage_prob), dst], stdout=FNULL, stderr=subprocess.STDOUT)



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dst-dir', type=str, metavar='DIR', default=os.getcwd())
    parser.add_argument('-o', '--outages', type=int, metavar='NUM', default=12)
    parser.add_argument('topologies', type=str, nargs="+", metavar='topo.json')
    args = parser.parse_args()
    make_experiments(args)
