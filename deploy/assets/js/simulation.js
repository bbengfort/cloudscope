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

  Simulation = function(selector, url, options) {

    this.url     = null;
    this.svg     = null;
    this.elem    = null;
    this.nodes   = [];
    this.margins = config.margins;

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
            // Get node objects for the source and target
            var source = self.nodes[link.source];
            var target = self.nodes[link.target];

            // Add source and target connections (undirected graph).
            // Note, only draw one of the connections, not both.
            source.addConnection(link, target).draw(ring);
            target.addConnection(link, source);
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
