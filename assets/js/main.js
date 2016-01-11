/*
 * main.js
 * The main javascript program for the CloudScope simulation
 *
 * Author:  Benjamin Bengfort <bengfort@cs.umd.edu>
 * Created: Sun Jan 10 13:17:07 2016 -0500
 *
 * Dependencies:
 *  - jquery
 *  - underscore
 */

var simulation;

$(document).ready(function() {

  // Fetch the simulation data to begin writing it to the screen.
  simulation = Simulation("#simulation", 'data/simulation.json');

  // TODO: Clean this up.
  $(".btnSnapshot").click(function() {
    simulation.snapshot();
  });
});
