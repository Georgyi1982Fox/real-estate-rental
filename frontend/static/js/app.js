(function () {
  'use strict';
  
  document.addEventListener('alpine:init', function () {
    Alpine.data('app', function () {
      return {
        open: false,
        loading: false,
        error: null
      };
    });
  });
}());
