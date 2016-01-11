[![Stories in Ready](https://badge.waffle.io/bbengfort/cloudscope.png?label=ready&title=Ready)](https://waffle.io/bbengfort/cloudscope)
# CloudScope

**Visualization of distributed systems and communications.**

[![Lens capped lunar eclipse of 2010][eclipse.jpg]][eclipse_flickr]

## Basic Plan

Right now the plan is to have the cloudscope package generate a static site, which will then be placed into the `gh-pages` repository for hosting. A simple static webserver can serve that site for development. Generation of the static site, in this case, is simply the generation of JSON data from graphs that are constructed by the cloudscope utility.

## About

Simple repository to visualize examples of data flow in distributed systems. Inspired by [The Secret Lives of Data](http://thesecretlivesofdata.com/raft/) and [RaftScope](https://github.com/ongardie/raftscope).

The photo used in this README, &ldquo;[Lens capped lunar eclipse of 2010][eclipse_flickr]&rdquo; by [John](https://www.flickr.com/photos/jahdakinebrah/) is used under a [CC BY-NC 2.0](https://creativecommons.org/licenses/by-nc/2.0/) creative commons license.

[eclipse.jpg]: docs/img/eclipse.jpg
[eclipse_flickr]: https://flic.kr/p/93AzEB
