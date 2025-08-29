import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

const firebaseConfig = {
apiKey: "AIzaSyAizFfOp7Lz6oYt8rnU4u5bpC1LhFBT3bc",
  authDomain: "education-419f2.firebaseapp.com",
  projectId: "education-419f2",
  storageBucket: "education-419f2.firebasestorage.app",
  messagingSenderId: "509919981380",
  appId: "1:509919981380:web:e55ae75d552b41f8577111",
  measurementId: "G-T8M1LJ4VQV"
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

export { db };
