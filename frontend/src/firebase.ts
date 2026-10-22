import {
  connectAuthEmulator,
  getAuth,
  type Auth,
} from "firebase/auth";
import {
  connectDataConnectEmulator,
  getDataConnect,
  type DataConnect,
} from "firebase/data-connect";
import { initializeApp, type FirebaseApp } from "firebase/app";
import { connectorConfig } from "@dataconnect/generated";

export type FirebaseServices = {
  app: FirebaseApp;
  auth: Auth;
  dataConnect: DataConnect;
};

let services: FirebaseServices | null = null;

export function getFirebaseServices(): FirebaseServices {
  if (services) return services;

  const firebaseConfig = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
  };
  const missing = Object.entries(firebaseConfig)
    .filter(([, value]) => !value)
    .map(([key]) => key);
  if (missing.length) {
    throw new Error(`Missing Firebase web config: ${missing.join(", ")}`);
  }

  const app = initializeApp(firebaseConfig);
  const auth = getAuth(app);
  const dataConnect = getDataConnect(app, connectorConfig);

  if (import.meta.env.DEV && import.meta.env.VITE_USE_FIREBASE_EMULATORS !== "false") {
    connectAuthEmulator(auth, "http://127.0.0.1:9099", { disableWarnings: true });
    connectDataConnectEmulator(dataConnect, "127.0.0.1", 9399);
  }

  services = { app, auth, dataConnect };
  return services;
}
