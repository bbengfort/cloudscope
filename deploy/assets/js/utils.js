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
     * An infinite sequence iterator for auto incrementing ids.
     */
    Sequence: function(start) {

      this.value = start || 0;

      this.next  = function() {
        this.value += 1;
        return this.value;
      }

      return this;
    },

    /*
     * Creates an SVG element to add via jquery.
     * http://www.benknowscode.com/2012/09/using-svg-elements-with-jquery_6812.html
     */
    SVG: function(tag) {
      return document.createElementNS('http://www.w3.org/2000/svg', tag);
    },

    /*
     * Pass in the selector for a form, this method uses jQuery's serializeArray
     * method to map the data in the form to an object for json.
     */
    formData: function(selector) {
      return _.object(_.map($(selector).serializeArray(), function(obj) {
        return [obj.name, obj.value];
      }));
    },

  };

  // Random "package" for generating random numbers easily.
  random = {

    /*
     * Wrapper for Math.random
     */
    random: function() { return Math.random(); },

    /*
     * Uses central limit theorem and resampling to generate normal random.
     */
    normal: function(mu, sigma, nsamples) {
      if(!nsamples) nsamples = 6;
      if(!sigma) sigma = 1;
      if(!mu) mu = 0;

      var total = 0;
      for (var i=0 ; i < nsamples ; i++) {
        total += Math.random()
      }

      return sigma * (total - nsamples / 2) / (nsamples / 2) + mu;
    },

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

  // Statistics "package" for computing descriptive statistics.
  stats = {

    // Computes the mean of a set of values.
    mean: function(values) {
      if (values.length == 0) return 0.0;

      var sum = _.reduce(values, function(sum, val) {
        return sum + val;
      }, 0);

      var avg = sum / values.length;
      return avg;

    },

    // Computes the standard deviation of a set of values
    stddev: function(values) {
      if (values.length == 0) return 0.0;

      var avg = stats.mean(values);

      var squareDiffs = _.map(values, function(val) {
        var diff = val - avg;
        return diff * diff;
      });

      var avgSquareDiff = stats.mean(squareDiffs);
      return Math.sqrt(avgSquareDiff);

    },

  };

})();
