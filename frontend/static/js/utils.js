(function () {
  'use strict';
  //ვქმნით binaUtils უტილიტს
  window.binaUtils = {
    formatPrice: function (value, currency) {
      const amount = Number(value);
      if (!Number.isFinite(amount)) return '';
      return new Intl.NumberFormat('ka-GE', { maximumFractionDigits: 0 }).format(amount) + ' ' + (currency || '₾');
    }
  };
}());
