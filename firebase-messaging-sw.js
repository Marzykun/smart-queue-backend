importScripts("https://www.gstatic.com/firebasejs/9.6.10/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/9.6.10/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: "AIzaSyD6yCxxnELKEnI6uiv010kchd9D0gA8S9E",
  authDomain: "smart-queue-501ad.firebaseapp.com",
  projectId: "smart-queue-501ad",
  messagingSenderId: "636720315516",
  appId: "1:636720315516:web:b4adb6a038649dcd16ddf9"
});

const messaging = firebase.messaging();

// 🔥 BACKGROUND MESSAGE HANDLER
messaging.onBackgroundMessage(function(payload) {
  console.log("Received background message ", payload);

  const title = payload.notification?.title || "Queue Update";
  const options = {
    body: payload.notification?.body || "Your turn is coming!",
    icon: "/icon.png"
  };

  self.registration.showNotification(title, options);
});
