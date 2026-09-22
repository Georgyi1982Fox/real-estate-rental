(function () {
  'use strict';

  const THEME_COLOR = { light: '#F8FAFC', dark: '#0F172A' };

  function syncThemeColorMeta(scheme) {
    const meta = document.getElementById('theme-color-meta');
    if (meta) meta.setAttribute('content', THEME_COLOR[scheme] || THEME_COLOR.light);
  }

  function applyColorScheme(scheme) {
    document.documentElement.dataset.telegramTheme = scheme;
    syncThemeColorMeta(scheme);
  }

  document.addEventListener('DOMContentLoaded', function () {
    const webApp = window.Telegram && window.Telegram.WebApp;
    if (!webApp) {
      //Telegram-ის გარეთ (ჩვეულებრივ ბრაუზერში) სისტემურ თემას მივყვებით
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      syncThemeColorMeta(media.matches ? 'dark' : 'light');
      media.addEventListener('change', function (e) {
        syncThemeColorMeta(e.matches ? 'dark' : 'light');
      });
      return;
    }

    webApp.ready();  //მზადაა
    webApp.expand(); //მთელს ეკრაზე გაშლა

    //ნათელი ან ბნელი თემა
    if (webApp.colorScheme) {
      applyColorScheme(webApp.colorScheme);
    }

    webApp.onEvent('themeChanged', function () {
      applyColorScheme(webApp.colorScheme);
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
