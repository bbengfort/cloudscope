# CloudScope

![Consistency Simulation Wireframe](img/wireframe.png)
**Simulation and visualization of distributed systems and communications.**

The original plan for CloudScope was to be a static site generator that would provide a visual simulation along the lines of [The Secret Lives of Data](http://thesecretlivesofdata.com/raft/) and [RaftScope](https://github.com/ongardie/raftscope). Since then, it has become an intricate distributed systems simulator that uses SimPy for discrete event simulation of message passing between replicas that implement a variety of consistency protocols. CloudScope is used for the research of distributed systems at the University of Maryland.

CloudScope's primary features and functionality are:

- Simulation of a network of replicas described by a JSON topology
- Generation of a workload of accesses or use of manual traces
- Implementation of a variety of consistency and consensus algorithms
- Analysis of the results of the simulations for various properties
- Interactive visualization provided by an SVG/JavaScript animation

CloudScope is continuing to evolve, so if you have any questions, please get in contact with us by messaging us through the GitHub issues.

## Getting Started

This quick start is intended to get you setup with CloudScope in development mode so that you can tweak and run the simulations. CloudScope is still in alpha, so no packaging has been prepared for PyPi, etc.

1. Fork the repository and clone your forked copy.

    ```
    $ git clone git@github.com:bbengfort/cloudscope.git
    $ cd cloudscope
    ```

2. Create a virtual environment and install the dependencies.

    ```
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt
    ```

3. Add the project path to your `$PYTHONPATH` via the virtualenv

    ```
    $ echo $(pwd) > venv/lib/python2.7/site-packages/cloudscope.pth
    ```

4. Create your local configuration file. You do a lot of experimental configurations in this file:

    ```
    $ cp conf/cloudscope-example.yaml conf/cloudscope.yaml
    ```

5. Run the tests to make sure that everything is ok

    ```
    $ make test
    ```

6. At this point you can start using the `scope.py` utility:

    ```
    $ python scope.py --help
    ```

In order to run a simulation you need a topology, many of which are in the `deploy` folder for visualization. Try running a Raft consensus simulation as follows:

    ```
    $ python scope.py simulate deploy/data/raft.json
    ```

You should see a log of the simulation, as well as results written to your local directory.

## Interactive Visualization

Right now the plan is to have the `cloudscope` package generate a static site, which will then be placed into the `gh-pages` branch for hosting via GitHub static pages. A simple static web server can serve that site for development. Generation of the static site, in this case, is simply the generation of JSON data from graphs that are constructed by the `cloudscope` utility.

The site is deployed to a folder called `deploy` in the root of the repository. It is this folder that is synchronized with the `gh-pages` branch. A simple server has been setup to statically render that folder in development. To run the server, simply:

```bash
$ python scope.py serve
```

You can then navigate to [http://localhost:8080](http://localhost:8080) in your web browser and the interactive visualization will appear.
