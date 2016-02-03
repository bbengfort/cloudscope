/*
 * replica.js
 * Implements Replica functionality for the simulation.
 *
 * Author:  Benjamin Bengfort <bengfort@cs.umd.edu>
 * Created: Mon Jan 11 20:11:33 2016 -0500
 *
 * Dependencies:
 *  - jquery
 *  - underscore
 */

 (function() {

  // Replica object to simulate devices on the file system
  Replica = function(sim, options) {

    this.id    = null;
    this.sim   = null;
    this.svg   = null;
    this.label = null;
    this.type  = null;

    this.consistency = null;
    this.layout      = null;

    this.comms = {};
    this.files = {};

    // Initializes a replica based on node data from a JSON graph.
    this.init = function(sim, node) {
      this.id    = node.id;
      this.sim   = sim
      this.label = node.label || "Replica " + node.id;
      this.type  = node.type || "storage";
      this.files = node.files || {};
      this.consistency = node.consistency || "strong";

      return this;
    };

    // Creates a new version (file) and replicates it.
    this.create = function() {
      // Create a new file with the version information
      var vers = new Version(0, {
        creator: self,
        level: this.consistency,
      })

      // Add the file to our storage
      // And replicate the new file across the network
      this.files[vers.version] = vers;
      this.sim.updateState();
      this.broadcast(vers);
    };

    // Updates a particular version (forks) and replicates it.
    this.update = function(version) {
      var vers = this.files[version];
      var fork = vers.fork();

      // Replace the file we have in our storage with the new version.
      // and replicate the update across the network (updating the sim)
      this.files[fork.version] = fork;
      this.sim.updateState();
      this.broadcast(fork);
    };

    // Sends a message to the destination
    // For now message can be anything, dst must be a replica id.
    this.send = function(msg, dst, options) {
      var conn = this.comms[dst];

      // Add the message properties like network latency
      options  = options || {};
      options  = _.defaults(options, {
        delay: conn.getLatency(),
      });

      return new Message(this, conn.target, msg, options);
    };

    // Handler for receiving a message
    this.recv = function(msg) {
      var self = this;

      // If we have an acknowledgement message; do nothing
      if (msg.payload == consts.ACK) return;

      var vers = msg.payload;
      if (!self.files[vers.version]) {
          // Add the version to your files.
          // Update the simulation state with the new version update.
          self.files[vers.version] = vers;
          vers.addReplica(self.sim.nodes.length);
          self.sim.updateState();

          // Send updates to everyone else
          _.each(this.comms, function(conn) {
            if (conn.target != msg.source) {
              return msg.clone(self, conn.target, {delay: conn.getLatency()});
            }
          });
      }

      // Send acknowledgment
      options = {
        delay: this.comms[msg.source.id].getLatency(),
        class: 'response'
      }
      var response = new Message(this, msg.source, "ACK", options);
      console.log(
        s.sprintf(
          "%s received message from %s in %dms",
          this.label, msg.source.label, msg.options.delay
        )
      );

    };

    // Broadcast a message to all connected nodes
    this.broadcast = function(msg) {
      var self = this;
      return _.map(self.comms, function(link) {
        return self.send(msg, link.target.id);
      });
    };

    // Adds connections based on link data from a JSON graph.
    this.addConnection = function(link, replica) {
      var connection = new Connection(this.sim, this, replica, link);
      this.comms[replica.id] = connection;
      return connection;
    };

    // Draws the node to the parent simulation
    // Must take a layout parameter for the position of the node.
    this.draw = function(layout) {
      var self = this;
      this.layout = layout

      // The node icon group
      this.svg = $(utils.SVG('g'))
        .attr("id", this.id)
        .attr("class", "replica consistency-" + this.consistency)
        .click(function() { self.create(); })
        .appendTo($("#graph", this.sim.svg));

      // The node circle
      $(utils.SVG('circle'))
        .attr(layout)
        .appendTo(this.svg);

      // The icon circle
      $(utils.SVG('circle'))
        .attr({"cx": layout.cx, "cy": layout.cy, r: (layout.r * .75)})
        .attr("filter", "url(#" + this.type + ")")
        .appendTo(this.svg);

      // The label of the node
      var label = {
        "text-anchor": "middle",
        "x": layout.cx,
        "class": "label"
      }

      // Move above if above the fold else move below
      if (layout.cy < (this.sim.height() / 2)) {
        label.y = layout.cy - 8 - layout.r;
      } else {
        label.y = layout.cy + 18 + layout.r;
      }

      $(utils.SVG('text'))
        .attr(label)
        .text(this.label)
        .appendTo(this.svg);
    }

    // Clears the drawing of this replica from the simulation.
    this.clear = function() {
      this.svg.remove();
    };

    return this.init(sim, options);
  };

  // Auto increment sequence for version ids.
  var sequence = new utils.Sequence();

  // Implement a piece of file version meta data
  Version = function(parent, options) {

    this.parent     = null;  // create a tree of version meta data
    this.version    = null;  // version id (auto increment)
    this.creator    = null;  // the replica that created the version
    this.level      = null;  // the consistency level of the version meta
    this.created    = null;  // timestamp when created
    this.updated    = null;  // timestamp when updated
    this.replicas   = null;  // the number of times the version is replicated
    this.replicated = null;  // timestamp when completely replicated

    // Initialize version meta data
    this.init = function(parent, options) {
      options = options || {};

      this.parent   = parent;
      this.version  = sequence.next();
      this.creator  = options.creator || null;
      this.level    = options.level || null;
      this.created  = options.created || Date.now();
      this.updated  = options.updated || null;
      this.replicas = 1;

      return this;
    }

    // Fork a new version from this version
    this.fork = function(options) {
      this.updated = Date.now();

      options = options || {};
      options = _.defaults(options, {
        creator: this.creator,
        level: this.level,
        created: this.created,
        updated: this.updated,
      });

      return new Version(this, options)
    }

    // Add a new replica to the version
    // Requires the number of nodes in the network to determine "completeness"
    this.addReplica = function(n) {
      this.replicas += 1;
      if (this.replicas == n) {
        this.replicated = Date.now();
      }
    }

    // Returns the replication latency of the version
    this.getLatency = function() {
      if (this.replicated) {
        return this.replicated - this.created;
      } else {
        return null;
      }
    }

    return this.init(parent, options);
  };

})();
