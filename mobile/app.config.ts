export default {
  expo: {
    name: "MiAppMovil",
    slug: "MiAppMovil",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/iconApp.png",
    userInterfaceStyle: "light",
    newArchEnabled: true,
    splash: {
      image: "./assets/splash-icon.png",
      resizeMode: "contain",
      backgroundColor: "#ffffff"
    },
    ios: {
      supportsTablet: true
    },
    android: {
      adaptiveIcon: {
        foregroundImage: "./assets/adaptive-icon.png",
        backgroundColor: "#ffffff"
      },
      edgeToEdgeEnabled: true,
      package: "com.anonymous.MiAppMovil",
      permissions: [
        "INTERNET",
        "ACCESS_NETWORK_STATE"
      ]
    },
    web: {
      favicon: "./assets/iconApp.png"
    },

    // <- Aquí actualizamos extra para incluir eas.projectId (ya lo tenías)
    extra: {
      eas: {
        projectId: "7f5ca19f-9334-45c0-bad4-4e489757f4e4"
      },
      API_BASE_URL: process.env.EXPO_PUBLIC_API_BASE_URL ?? "https://djangoapp-6wxv.onrender.com"
    },

    // Añade esto: configuración requerida para EAS Update
    updates: {
      url: "https://u.expo.dev/7f5ca19f-9334-45c0-bad4-4e489757f4e4"
    },

    // Usa runtimeVersion por política de versión de app (recomendado)
    // Esto permite que EAS Update identifique compatibilidad por app version
    runtimeVersion: "1.0.0",

    plugins: [
      [
        "expo-build-properties",
        {
          "android": {
            "usesCleartextTraffic": true
          }
        }
      ]
    ]
  }
};
