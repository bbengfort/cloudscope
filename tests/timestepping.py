
import csv
import time
import simpy

from cloudscope.utils.decorators import timeit
from cloudscope.simulation.base import Process


class Stepper(Process):

    def __init__(self, env, steps):
        self.count = 0
        self.steps = steps
        super(Stepper, self).__init__(env)

    def run(self):
        while True:
            self.count += 1
            yield self.env.timeout(self.steps)


@timeit
def gogurt(steps, until=4320000):
    env   = simpy.Environment()
    proc  = Stepper(env, steps)

    env.run(until=until)
    return proc.count


if __name__ == '__main__':

    # Open up the output file for writing the data
    with open('timestepping.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(('steps', 'until', 'count', 'time'))

        # Conduct ten tests at different steps and max times.
        for until in xrange(1000000, 50000001, 5000000):
            for steps in xrange(1, 11):
                count, timer = gogurt(steps, until)
                writer.writerow((steps, until, count, timer.elapsed))
                print "completed {} checks in {}".format(count, timer)
