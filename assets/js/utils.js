/*
 * utils.js
 * Helper functions for global use in CloudScope.
 *
 * Author:  Benjamin Bengfort <bengfort@cs.umd.edu>
 * Created: Sun Jan 10 13:17:07 2016 -0500
 *
 * Dependencies:
 *  - jquery
 *  - underscore
 */

(function() {

  // Utilities "package" with helper functions.
  utils = {
    /*
     * Similar to humanize.intcomma - renders an integer with thousands-
     * separated by commas. Pass in an integer, returns a string.
     */
    intcomma: function(x) {
      return x.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    },

    /*
     * Parses a string boolean and returns a bool type.
     */
    parseBool: function(str) {
      if (typeof(str) === "boolean") {
        return str
      }

      return JSON.parse(
          str.toLowerCase()
            .replace('none', 'false')
            .replace('no','false')
            .replace('yes','true')
          );
    },

    /*
     * Creates an SVG element to add via jquery.
     * http://www.benknowscode.com/2012/09/using-svg-elements-with-jquery_6812.html
     */
    SVG: function(tag) {
      return document.createElementNS('http://www.w3.org/2000/svg', tag);
    }

  };

  // Random "package" for generating random numbers easily.
  random = {

    /*
     * Wrapper for Math.random
     */
    random: function() { return Math.random(); },

    /*
     * Returns a float between the minimum and the maximum value
     */
    randrange: function(min, max) {
      min = min || 0.0;
      max = max || 1.0;
      return Math.random() * (max - min) + min;
    },

    /*
     * Returns a random integer between the minimum and maximum value.
     * Note: using Math.round() will give you a non-uniform distribution!
     */
    randint: function(min, max) {
      min = min || 0;
      max = max || 1;
      return Math.floor(Math.random() * (max - min + 1)) + min;
    }
  };

})();
