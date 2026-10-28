// Firebase Configuration
const firebaseConfig = {
  apiKey: "AIzaSyA9z7Ur-wxubA7YFc-cnIakVpZI68BhEFI",
  authDomain: "algox-14cf7.firebaseapp.com",
  projectId: "algox-14cf7",
  storageBucket: "algox-14cf7.firebasestorage.app",
  messagingSenderId: "744939014509",
  appId: "1:744939014509:web:0b16875fed88cace7e3264",
  measurementId: "G-YMCQRCKMQC"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Initialize analytics
const analytics = firebase.analytics();
console.log("Firebase connected successfully!");
