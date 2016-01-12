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
  simulation = new Simulation("#simulation", 'data/simulation.json');

  // Register various other event handlers.
  // Create a PNG from the SVG and download it.
  $(".btnSnapshot").click(function() {
    simulation.snapshot();
  });

  // Save settings from the settings modal.
  $("#btnSaveSettings").click(function() {
    var data = utils.formData("#settingsForm")

    _.each(data, function(val, key) {
      val = parseInt(val); // temporary, need better parsing later.
      config[key] = val;
    });

    $("#settingsModal").modal('hide');
  });

  // Add current settings to the settings modal on show
  $("#settingsModal").on('show.bs.modal', function(e) {
    var data = utils.formData("#settingsForm")

    _.each(data, function(val, key) {
      $("#" + key).val(config[key]);
    });
  });

});
