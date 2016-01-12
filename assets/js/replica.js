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

   // Module Variables
   var sequence = new utils.Sequence();

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

     // Sends a message to the destination
     // For now message can be anything, dst must be a replica id.
     this.send = function(msg, dst, options) {
       var self = this;
       var conn = self.comms[dst];

       // Create a message with the version information
       msg = msg || {};
       msg = _.defaults(msg, {
         creator: self,
         version: sequence.next(),
         level: self.consistency
       });
       self.files[msg.version] = msg;

       // Add the message properties like network latency
       options  = options || {};
       options  = _.defaults(options, {
         delay: conn.getLatency(),
       });

       return new Message(self, conn.target, msg, options);
     };

     // Handler for receiving a message
     this.recv = function(msg) {
       var self = this;

       // "ACK" is currently the payload for an acknowledgement
       if (msg.payload != "ACK") {
         // Add the version to your files.
         if (!self.files[msg.payload.version]) {
             self.files[msg.payload.version] = msg.payload;

             // Send updates to everyone else
             _.each(this.comms, function(link) {
               if (link.target != msg.source) {
                 return msg.clone(self, link.target, {delay: link.getLatency()});
               }

             });
         }

         // Send acknowledgment
         options = {
           delay: this.comms[msg.source.id].getLatency(),
           class: 'response'
         }
         var response = new Message(this, msg.source, "ACK", options);
         console.log(this.label + " received message from " + msg.source.label + " in " + msg.options.delay + " milliseconds.");

       }
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
       this.layout = layout;

       // The node icon group
       this.svg = $(utils.SVG('g'))
         .attr("id", this.id)
         .attr("class", "replica consistency-" + this.consistency)
         .click(function() { self.broadcast(); })
         .appendTo(this.sim.svg);

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

     return this.init(sim, options);
   };

})();
