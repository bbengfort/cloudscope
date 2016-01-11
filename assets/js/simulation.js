/*
 * simulation.js
 * An object wrapper for a simulation in CloudScope
 *
 * Author:  Benjamin Bengfort <bengfort@cs.umd.edu>
 * Created: Sun Jan 10 15:22:41 2016 -0500
 *
 * Dependencies:
 *  - jquery
 *  - underscore
 */

(function() {

  Replica = function(env, options) {

    this.id    = null;
    this.env   = null;
    this.svg   = null;
    this.label = null;
    this.type  = null;

    this.consistency = null;
    this.layout      = null;

    this.comms = [];
    this.files = [];

    // Initializes a replica based on node data from a JSON graph.
    this.init = function(env, node) {
      this.id    = node.id;
      this.env   = env
      this.label = node.label || "Replica " + node.id;
      this.type  = node.type || "storage";
      this.files = node.files || [];
      this.consistency = node.consistency || "strong";

      return this;
    }

    // Adds connections based on link data from a JSON graph.
    this.addConnection = function(link, replica) {
      var connection = {
        target: replica,       // replica destination
        type: link.connection, // constant or variable
        latency: link.latency  // either an integer or a min, max pair.
      }
      this.comms.push(connection);
      return connection;
    }

    // Draws the node to the parent environment
    // Must take a layout parameter for the position of the node.
    this.draw = function(layout) {
      this.layout = layout;

      // The node icon group
      this.svg = $(utils.SVG('g'))
        .attr("id", this.id)
        .attr("class", "replica consistency-" + this.consistency)
        .appendTo(this.env.svg);

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
      if (layout.cy < (this.env.height() / 2)) {
        label.y = layout.cy - 8 - layout.r;
      } else {
        label.y = layout.cy + 18 + layout.r;
      }

      $(utils.SVG('text'))
        .attr(label)
        .text(this.label)
        .appendTo(this.svg);
    }

    return this.init(env, options);
  };

  Simulation = function(selector, url, options) {

    this.url     = null;
    this.svg     = null;
    this.elem    = null;
    this.nodes   = [];
    this.margins = {
      top: 38,
      right: 10,
      bottom: 38,
      left: 10
    }


    // Initializes the simulation by loading data from a URL.
    this.init = function(selector, url, options) {

      // Set object properties
      this.url  = url;
      this.elem = $(selector);
      this.svg  = $("svg", this.elem);

      // Use the options defaults to update
      if (options) {
        if (options.margins) {
           this.margins = _.defaults(options.margins, this.margins);
        }
      }

      // Add the layout ring to the center of the svg.
      $('#ring', this.svg).attr(this.ringDimension());

      // Load data and return
      this.load();
      return this;

    };

    // Loads the data from the data path
    this.load = function() {
      var self = this;
      $.get(self.url)
        .done(function(data) {
          // Add all the replicas to our simulation
          self.nodes  = _.map(data.nodes, function(obj) {
            return new Replica(self, obj);
          });

          // Some helper variables for loading data
          var ring    = self.ringDimension();
          var layout  = self.ringLayout(self.nodes.length);
          var network = $(utils.SVG('g'))
            .attr("id", "network")
            .appendTo(self.svg);

          // Draw the nodes onto the graph
          _.each(_.zip(self.nodes, layout), function(item) {
            var node = item[0];
            var layout = item[1];

            node.draw(layout);
          });

          // Add all the communiucation edges between replicas
          _.each(data.links, function(link) {
            source = self.nodes[link.source];
            target = self.nodes[link.target];

            // Add source and target connections (undirected graph).
            source.addConnection(link, target);
            target.addConnection(link, source);

            sp = "M" + source.layout.cx + "," + source.layout.cy;
            ep = target.layout.cx + "," + target.layout.cy;
            cp = "Q" + ring.cx + "," + ring.cy;

            // Draw the edges onto the graph
            $(utils.SVG("path"))
              .attr("d", sp + " " + cp + " " + ep)
              .attr("class", "link " + link.connection)
              .appendTo(network);
          });

          console.log("Simulation loaded from " + self.url);
        })
        .fail(function(jqxhr, status, error) {
          console.log("ERROR (" + status + "): " + error);
        });
    };

    // Computes the ring dimensions to create a layout
    this.ringDimension = function() {
        return {
          cx: this.center()[0],
          cy: this.center()[1],
          r: (this.height() / 2) - this.margins.top - this.margins.bottom
        };
    };

    // Computes the ring layout of the simulation where n is the # of nodes.
    this.ringLayout = function(n) {
      var dims  = this.ringDimension();
      var theta = ((Math.PI * 2) / n);

      // Return a list of the layouts for each circle on the ring.
      return _.times(n, function(idx) {
        var angle = (theta * idx) - (Math.PI / 2);

        return {
          cx: (dims.r * Math.cos(angle) + dims.cx),
          cy: (dims.r * Math.sin(angle) + dims.cy),
          r: 45
        };
      });
    };

    // Helper function to get the width from the element
    // If the inner argument is true, the margins are subtracted
    this.width = function(inner) {
      if (inner) {
        return this.elem.width() - this.margins.left - this.margins.right;
      } else {
        return this.elem.width();
      }

    };

    // Helper function to get the height from the element
    // If the inner argument is true, the margins are subtracted
    this.height = function(inner) {
      if (inner) {
        return this.elem.height() - this.margins.top - this.margins.bottom;
      } else {
        return this.elem.height();
      }

    };

    // Helper function to get the center of the element
    this.center = function() {
      return [
        this.width() / 2,
        this.height() / 2
      ];
    }

    // Helper function to encode the simulation as an image to download
    // http://spin.atomicobject.com/2014/01/21/convert-svg-to-png/
    this.snapshot = function() {
      return saveSvgAsPng(this.svg[0], 'snapshot.png');
    }

    return this.init(selector, url, options);
  };

})();
