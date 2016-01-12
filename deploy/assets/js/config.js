/*
 * config.js
 * Modifiable configuration values for the entire simulation.
 *
 * Author:  Benjamin Bengfort <bengfort@cs.umd.edu>
 * Created: Mon Jan 11 20:17:39 2016 -0500
 *
 * Dependencies:
 *  - jquery
 *  - underscore
 */

(function() {

  // Simulation constants
  consts = {

    // Network connection types
    CONSTANT: "constant",
    VARIABLE: "variable",

    // Constant message payloads
    ACK: "ACK", 
  }

  // Modifiable configuration values.
  config = {

    // Set this to 1 for realtime, or a factor < 10 for slow motion
    slowmo: 3,

    // Default latency for a new connection
    default_latency: 800,

    // Margins for the primary simulation SVG
    margins: {
      top: 38,
      right: 10,
      bottom: 38,
      left: 10
    },

  };

})();
