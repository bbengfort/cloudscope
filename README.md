# CloudScope

[![Build Status](https://travis-ci.org/bbengfort/cloudscope.svg?branch=master)](https://travis-ci.org/bbengfort/cloudscope)
[![Coverage Status](https://coveralls.io/repos/github/bbengfort/cloudscope/badge.svg?branch=master)](https://coveralls.io/github/bbengfort/cloudscope?branch=master)
[![Stories Ready](https://badge.waffle.io/bbengfort/cloudscope.png?label=ready&title=ready)](https://waffle.io/bbengfort/cloudscope)

**Simulation and visualization of consistency in distributed systems.**

[![Lens capped lunar eclipse of 2010][eclipse.jpg]][eclipse_flickr]

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

## Experimentation

Currently we are running simulation experiments with replicas that implement various consensus and consistency algorithms in a variety of topologies and environments. The target is to produce results as follows:

Experimental control variables:

- increasing WAN latency, e.g. T (tick)
- increasing number of nodes
- increasing amounts of failure

Metrics:

- # forks
- # stale reads
- % visible (for full replication)
- % committed
- # of messages
- read latency
- write latency
- visibility latency
- commit latency

## Contributing

[![Throughput Graph](https://graphs.waffle.io/bbengfort/cloudscope/throughput.svg)](https://waffle.io/bbengfort/cloudscope/metrics)

CloudScope is open source, and I'd love your help. In particular, we are looking for folks to add replicas that add a variety of consensus algorithms (there are quite a few) to the mix, such as Paxos, ePaxos, Fast Paxos, and more. For more on this project, please ask about the &ldquo;Consensus Shootout&rdquo; If you would like to contribute, you can do so in the following ways:

1. Add issues or bugs to the bug tracker: [https://github.com/bbengfort/cloudscope/issues](https://github.com/bbengfort/cloudscope/issues)
2. Work on a card on the dev board: [https://waffle.io/bbengfort/cloudscope](https://waffle.io/bbengfort/cloudscope)
3. Create a pull request in Github: [https://github.com/bbengfort/cloudscope/pulls](https://github.com/bbengfort/cloudscope/pulls)

Note that labels in the Github issues are defined in the blog post: [How we use labels on GitHub Issues at Mediocre Laboratories](https://mediocre.com/forum/topics/how-we-use-labels-on-github-issues-at-mediocre-laboratories).

To get started, fork the repository so that you have a local copy to work on. The repository is set up in a typical production/release/development cycle as described in _[A Successful Git Branching Model](http://nvie.com/posts/a-successful-git-branching-model/)_. Make sure that you checkout and are working on the `develop` branch at all times. Pull requests to master will not be accepted! A typical workflow is as follows:

1. Select a card from the [dev board](https://waffle.io/bbengfort/cloudscope) - preferably one that is "ready" then move it to "in-progress".

2. Create a branch off of develop called "feature-[feature name]", work and commit into that branch.

        ~$ git checkout -b feature-myfeature develop

3. Once you are done working (and everything is tested) merge your feature into develop.

        ~$ git checkout develop
        ~$ git merge --no-ff feature-myfeature
        ~$ git branch -d feature-myfeature
        ~$ git push origin develop

4. Repeat. Releases will be routinely pushed into master via release branches, then deployed to the server.

### Acknowledgements

Thank you for all your help contributing to make CloudScope a great project!

#### Maintainers

- Benjamin Bengfort: [@bbengfort](https://github.com/bbengfort/)

#### Contributors

- Your name here!

#### Attribution

The photo used in this README, &ldquo;[Lens capped lunar eclipse of 2010][eclipse_flickr]&rdquo; by [John](https://www.flickr.com/photos/jahdakinebrah/) is used under a [CC BY-NC 2.0](https://creativecommons.org/licenses/by-nc/2.0/) creative commons license.

## Changelog

The release versions that are tagged in Git. You can see the tags through the GitHub web application and download the tarball of the version you'd like.

The versioning uses a three part version system, "a.b.c" - "a" represents a major release that may not be backwards compatible. "b" is incremented on minor releases that may contain extra features, but are backwards compatible. "c" releases are bug fixes or other micro changes that developers should feel free to immediately update to.

### Version 0.4

* **tag**: [v0.4](https://github.com/bbengfort/cloudscope/releases/tag/v0.4)
* **deployment**: Wednesday, June 15, 2016
* **commit**: (see tag)

In the course of research, things change. This release is an attempt to create a fixture for the initial progression of the research. There will be some pivots in upcoming releases, but Version 0.4 represents a stable platform for running simulations of various kinds for consistency modeling in a distributed storage system. This release saw the addition of _many_ features and bug squashes. An enumeration of these additions is on the GitHub release page. Together these features show the course of research over the Spring semester, and relate to the papers that will be published via the Version 0.5 release of this code.

### Version 0.3

* **tag**: [v0.3](https://github.com/bbengfort/cloudscope/releases/tag/v0.3)
* **deployment**: Tuesday, February 23, 2016
* **commit**: [00c5dd7](https://github.com/bbengfort/cloudscope/commit/00c5dd71d86f94dce5fd31b254a1c690c5ec1a53)

This version implements the initial simulation prototype, and in particular handles eventual consistency and Raft quorum consistency. The two simulations that have been run and validated are homogenous consistency topologies (e.g. all eventual or all Raft). This version highlights the motivating examples for our work.

### Early Releases

Earlier releases that had the version 0.1 and 0.2 versions were MVP prototypes for the web visualization and the basic simulation. These releases were organized slightly differently, so they are not tagged in GitHub.

[eclipse.jpg]: docs/img/eclipse.jpg
[eclipse_flickr]: https://flic.kr/p/93AzEB
