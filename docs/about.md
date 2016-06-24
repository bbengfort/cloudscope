# About

CloudScope is a discrete event simulation of distributed storage systems coupled with utilities for visualization and analysis of the performance of algorithms meant for consistency and consensus. It is has been created as part of research at the University of Maryland.

## Contributing

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
