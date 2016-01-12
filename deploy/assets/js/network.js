/*
 * network.js
 * Implements communications between replicas and animates them.
 *
 * Author:  Benjamin Bengfort <bengfort@cs.umd.edu>
 * Created: Mon Jan 11 20:22:43 2016 -0500
 *
 * Dependencies:
 *  - jquery
 *  - underscore
 */

(function() {

  // Message object to simulate network communication
  Message = function(source, target, payload, options) {

    this.source  = source;
    this.target  = target;
    this.payload = payload;
    this.options = {
      delay: 1000,        // The message latency (or delay)
      class: 'message',   // Class to add to the message circle
      trigger: true,      // Trigger the message to send immediately
    };

    // Initializes the message
    this.init = function(options) {
      // Set default options
      options = options || {};
      this.options = _.defaults(options, this.options);

      if (options.trigger) {
        this.trigger();
      }

      // Return this for chaining
      return this;
    }

    // Sends the message
    this.trigger = function() {
      var self = this;

      // Prepare callback for message recv
      setTimeout(function() {
        self.target.recv(self);
      }, self.options.delay);

      // Animate the message
      self.animate();

      // Return this for chaining
      return self;
    };

    // Animates a message circle between nodes
    // TODO: follow the connection path rather than straight line.
    this.animate = function() {
      var circle = $(utils.SVG('circle'))
        .attr({'cx': this.source.layout.cx, 'cy': this.source.layout.cy, 'r': 8})
        .attr('class', this.options.class)
        .appendTo($("#network", this.source.sim.svg));

      circle.velocity({
        cx: this.target.layout.cx,
        cy: this.target.layout.cy
      }, {
        duration: this.options.delay,
        complete: function(elements) {
          _.each(elements, function(element) {
            $(element).remove();
          });
        }
      });
    }

    // Clones a message with a new source and target
    this.clone = function(source, target, options) {
      options = options || {};
      options = _.defaults(options, this.options)
      return new Message(source, target, this.payload, options);
    }

    return this.init(options);
  };

  // Connection manages network properties as well as visual paths.
  // Represents a unidirectional connection; bidirectional requires 2 connections
  Connection = function(sim, source, target, link) {

    this.sim     = null; // The parent simulation
    this.source  = null; // The source (sending) replica
    this.target  = null; // The target (destination) replica
    this.type    = null; // The connection type (constant or variable)
    this.latency = null; // Either a static integer or a min, max pair
    this.path    = null; // The svg path of the connection (bezier curve)

    this.init = function(sim, source, target, link) {
      this.sim     = sim;
      this.source  = source;
      this.target  = target;
      this.type    = link.connection || consts.CONSTANT;
      this.latency = link.latency || config.default_latency;

      // Return the connection object for use.
      return this;
    };

    // Computes the latency on demand for the connection.
    this.getLatency = function() {
      if (this.type == consts.VARIABLE) {
       var latency = random.randint(this.latency[0], this.latency[1]);
       return latency * config.slowmo;
      } else {
       return this.latency * config.slowmo;
      }
    };

    // Draw the bezier curve path onto the simulation.
    this.draw = function(ring) {
      ring = ring || this.sim.ringDimension();

      var sp = "M" + this.source.layout.cx + "," + this.source.layout.cy;
      var ep = this.target.layout.cx + "," + this.target.layout.cy;
      var cp = "Q" + ring.cx + "," + ring.cy;

      // Draw the edges onto the graph
      this.path = $(utils.SVG("path"))
        .attr("d", sp + " " + cp + " " + ep)
        .attr("class", "link " + this.type)
        .appendTo($("#network", this.sim.svg));
    };

    return this.init(sim, source, target, link);
  };

})();
