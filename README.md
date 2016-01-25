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

[eclipse.jpg]: docs/img/eclipse.jpg
[eclipse_flickr]: https://flic.kr/p/93AzEB
