(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', function () {
    const webApp = window.Telegram && window.Telegram.WebApp;
    if (!webApp) return;

    webApp.ready();  //მზადაა
    webApp.expand(); //მთელს ეკრაზე გაშლა
    
    //ნათელი ან ბნელი თემა
    if (webApp.colorScheme) {
      document.documentElement.dataset.telegramTheme = webApp.colorScheme;
    }

    webApp.onEvent('themeChanged', function () {
      document.documentElement.dataset.telegramTheme = webApp.colorScheme;
    });
  });
  //ვქმნით binaTelegram-ს შემდეგ გამოვიყენებთ როგორც ცვლადს
  window.binaTelegram = {
    haptic: function (type) {
      const feedback = window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.HapticFeedback;
      if (!feedback) return;
      if (type === 'success' || type === 'error' || type === 'warning') {
        feedback.notificationOccurred(type);
        return;
      }
      feedback.impactOccurred(type || 'light');
    }
  };
}());
