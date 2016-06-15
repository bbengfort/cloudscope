# CloudScope

[![Build Status](https://travis-ci.org/bbengfort/cloudscope.svg?branch=master)](https://travis-ci.org/bbengfort/cloudscope)
[![Coverage Status](https://coveralls.io/repos/github/bbengfort/cloudscope/badge.svg?branch=master)](https://coveralls.io/github/bbengfort/cloudscope?branch=master)
[![Stories Ready](https://badge.waffle.io/bbengfort/cloudscope.png?label=ready&title=ready)](https://waffle.io/bbengfort/cloudscope)

**Visualization of distributed systems and communications.**

[![Lens capped lunar eclipse of 2010][eclipse.jpg]][eclipse_flickr]

## Basic Plan

Right now the plan is to have the `cloudscope` package generate a static site, which will then be placed into the `gh-pages` repository for hosting. A simple static web server can serve that site for development. Generation of the static site, in this case, is simply the generation of JSON data from graphs that are constructed by the `cloudscope` utility.

### Working Links

The following are tabs that I have open when I'm working on either the simulation or the SVG visualization.

- [CloudScope](http://bbengfort.github.io/cloudscope/)
- [Waffle Dev Board](https://waffle.io/bbengfort/cloudscope)
- [Github Repository](https://github.com/bbengfort/cloudscope)

#### Simulation

- [SimPy Reference](https://simpy.readthedocs.org/en/latest/)

#### SVG Visualization

- [Underscore.js Reference](http://underscorejs.org/)
- [jQuery Reference](https://jquery.com/)
- [Velocity.js Reference](http://julian.com/research/velocity/)
- [Bootstrap Reference](http://getbootstrap.com/css/)
- [Font Awesome Reference](https://fortawesome.github.io/Font-Awesome/cheatsheet/)
- [SVG Reference](https://developer.mozilla.org/en-US/docs/Web/SVG)


## About

Simple repository to visualize examples of data flow in distributed systems. Inspired by [The Secret Lives of Data](http://thesecretlivesofdata.com/raft/) and [RaftScope](https://github.com/ongardie/raftscope).

The photo used in this README, &ldquo;[Lens capped lunar eclipse of 2010][eclipse_flickr]&rdquo; by [John](https://www.flickr.com/photos/jahdakinebrah/) is used under a [CC BY-NC 2.0](https://creativecommons.org/licenses/by-nc/2.0/) creative commons license.

## Other Information

[![Throughput Graph](https://graphs.waffle.io/bbengfort/cloudscope/throughput.svg)](https://waffle.io/bbengfort/cloudscope/metrics)

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
