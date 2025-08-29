<template>
  <v-container fluid class="dashboard-container" :class="{ 'dark-theme': isDarkMode }">
 

    <!-- Admin Dashboard Stats Cards -->
    <v-row class="mb-6">
      <v-col cols="12">
        <h1 class="text-h4 font-weight-bold mb-4 mt-10 dashboard-title">Admin Dashboard</h1>
      </v-col>
      <v-col v-for="(stat, index) in statsCards" :key="index" cols="12" sm="6" md="4">
        <v-card 
          class="stat-card" 
          :class="[`stat-card--${stat.variant}`, { 'stat-card--dark': isDarkMode }]" 
          :dark="isDarkMode"
          elevation="3" 
          rounded="lg"
        >
          <div class="stat-card__icon-wrapper">
            <v-icon size="32" :color="stat.iconColor">{{ stat.icon }}</v-icon>
          </div>
          <div class="stat-card__content">
            <div class="stat-card__title">{{ stat.title }}</div>
            <div class="stat-card__value">{{ stat.value }}</div>
          </div>
          <div class="stat-card__trend" v-if="stat.trend">
            <v-icon size="16" :color="stat.trendColor">{{ stat.trendIcon }}</v-icon>
            <span :class="`text-${stat.trendColor}`">{{ stat.trend }}</span>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Loading Indicator -->
    <v-row v-if="isLoading">
      <v-col cols="12" class="text-center">
        <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
        <p class="mt-3 loading-text">Ma'lumotlar yuklanmoqda...</p>
      </v-col>
    </v-row>

    <!-- Dashboard Overview Section -->
    <template v-else>
      <DashboardOverview class="mt-6"></DashboardOverview>
    </template>
  </v-container>
</template>

<script>
import { db } from "@/firebaseConfig";
import { collection, getDocs } from "firebase/firestore";

export default {
  name: 'AdminDashboard',

  data() {
    return {
      totalStudents: 0,
      totalPayments: 0,
      totalPass: 1,
      isLoading: true,

      // Dark/Light mode variables
      isDarkMode: false,
      themeCheckInterval: null,
      lastTheme: null,
      storageListener: null,
    };
  },

  computed: {
    statsCards() {
      return [
        {
          title: "Jami O'quvchilar",
          value: `${this.totalStudents} ta`,
          variant: "primary",
          icon: "mdi-account-group",
          iconColor: "primary",
          trend: "+12% oylik",
          trendIcon: "mdi-arrow-up",
          trendColor: "success"
        },
        {
          title: "Jami To'lovlar",
          value: `${this.formatCurrency(this.totalPayments)} so'm`,
          variant: "success",
          icon: "mdi-cash-multiple",
          iconColor: "success",
          trend: "+5% oylik",
          trendIcon: "mdi-arrow-up",
          trendColor: "success"
        },
        {
          title: "Jami O'qituvchilar",
          value: `${this.totalPass} ta`,
          variant: "info",
          icon: "mdi-school-outline",
          iconColor: "info",
          trend: "O'qituvchilar oyga teng",
          trendIcon: "mdi-minus",
          trendColor: "grey"
        }
      ];
    }
  },

  watch: {
    // isDarkMode o'zgarsa avtomatik Vuetify theme ni yangilash
    isDarkMode(newValue) {
      this.$vuetify.theme.dark = newValue;
    },
  },

  async created() {
    // Load theme from localStorage
    this.loadTheme();
    this.lastTheme = localStorage.getItem('theme');

    // Setup storage event listener (boshqa tab/window da o'zgarish uchun)
    this.setupStorageListener();

    // Setup polling intervals (bir xil tab ichida o'zgarish uchun)
    this.setupPollingIntervals();

    // Load dashboard data
    this.fetchData();
  },

  beforeDestroy() {
    // Barcha intervallarni tozalash
    if (this.themeCheckInterval) {
      clearInterval(this.themeCheckInterval);
    }

    // Storage listener ni o'chirish
    if (this.storageListener) {
      window.removeEventListener('storage', this.storageListener);
    }

    // Custom event listener ni o'chirish
    window.removeEventListener('themeChanged', this.handleThemeChanged);
  },

  methods: {
    // Theme yuklash
    loadTheme() {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) {
        this.isDarkMode = savedTheme === 'dark';
      }
      this.$vuetify.theme.dark = this.isDarkMode;
    },

    // Storage event listener ni o'rnatish (boshqa tab/window uchun)
    setupStorageListener() {
      this.storageListener = (event) => {
        console.log('Storage event triggered:', event.key, event.newValue);

        if (event.key === 'theme') {
          this.isDarkMode = event.newValue === 'dark';
          this.lastTheme = event.newValue;
          this.$forceUpdate();
        }
      };

      window.addEventListener('storage', this.storageListener);
    },

    // Polling intervallarni o'rnatish (bir xil tab ichida o'zgarish uchun)
    setupPollingIntervals() {
      // Theme o'zgarishini tekshirish
      this.themeCheckInterval = setInterval(() => {
        this.checkThemeChange();
      }, 500); // Har 500ms da tekshirish
    },

    // Theme o'zgarishini tekshirish
    checkThemeChange() {
      const currentTheme = localStorage.getItem('theme');
      if (currentTheme !== this.lastTheme) {
        console.log('Theme changed from', this.lastTheme, 'to', currentTheme);
        this.lastTheme = currentTheme;
        this.isDarkMode = currentTheme === 'dark';
        this.$forceUpdate();
      }
    },

    // Custom event handlerlar
    handleThemeChanged(event) {
      console.log('Custom theme event:', event.detail);
      this.isDarkMode = event.detail.isDark;
      this.$forceUpdate();
    },

    // Toggle dark/light mode
    toggleTheme() {
      this.isDarkMode = !this.isDarkMode;
      const theme = this.isDarkMode ? 'dark' : 'light';
      localStorage.setItem('theme', theme);
      this.$vuetify.theme.dark = this.isDarkMode;

      // Dispatch custom event for other components
      window.dispatchEvent(new CustomEvent('themeChanged', {
        detail: { isDark: this.isDarkMode }
      }));
    },

    formatCurrency(value) {
      return new Intl.NumberFormat('uz-UZ').format(value);
    },

    async fetchData() {
      try {
        this.isLoading = true;

        // Fetch students data
        const studentsSnapshot = await getDocs(collection(db, "students"));
        this.totalStudents = studentsSnapshot.size;

        // Calculate total payments
        this.totalPayments = studentsSnapshot.docs.reduce((total, doc) => {
          const studentData = doc.data();
          let paymentValue = studentData.payment || 0;

          // Convert string payment values to numbers
          if (typeof paymentValue === "string") {
            paymentValue = paymentValue.replace(/[^\d.-]/g, "");
          }

          const parsedPayment = parseFloat(paymentValue);
          return !isNaN(parsedPayment) ? total + parsedPayment : total;
        }, 0);

        // Fetch teachers data
        const teachersSnapshot = await getDocs(collection(db, "teachers"));
        this.totalPass = teachersSnapshot.size;
      } catch (error) {
        console.error("Error fetching dashboard data:", error);
        this.$toast.error("Ma'lumotlarni yuklashda xatolik yuz berdi");
      } finally {
        this.isLoading = false;
      }
    }
  }
};
</script>

<style scoped>
/* Light theme styles */
.dashboard-container {
  padding: 24px;
  background-color: #f5f7fa;
  min-height: 100vh;
  transition: all 0.3s ease;
}

.dashboard-title {
  color: #212121;
  transition: color 0.3s ease;
}

.loading-text {
  color: #757575;
  transition: color 0.3s ease;
}

.theme-toggle-btn {
  margin-bottom: 16px;
}

/* Dark theme styles */
.dashboard-container.dark-theme {
  background-color: #121212;
  color: #ffffff;
}

.dashboard-container.dark-theme .dashboard-title {
  color: #ffffff;
}

.dashboard-container.dark-theme .loading-text {
  color: #b0b0b0;
}

/* Stat cards - Base styles */
.stat-card {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 140px;
  padding: 20px;
  overflow: hidden;
  transition: all 0.3s ease;
  color: #212121;
  background-color: white;
}

/* Dark theme for stat cards - Fixed with higher specificity */
.stat-card.stat-card--dark {
  background-color: #1e1e1e !important;
  color: #ffffff !important;
}

.stat-card.stat-card--dark .stat-card__title {
  color: #b0b0b0 !important;
}

.stat-card.stat-card--dark .stat-card__value {
  color: #ffffff !important;
}

/* Additional override for Vuetify card background */
.dashboard-container.dark-theme .stat-card {
  background-color: #1e1e1e !important;
  color: #ffffff !important;
}

.dashboard-container.dark-theme .stat-card .stat-card__title {
  color: #b0b0b0 !important;
}

.dashboard-container.dark-theme .stat-card .stat-card__value {
  color: #ffffff !important;
}

/* Hover effects */
.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1) !important;
}

.stat-card.stat-card--dark:hover,
.dashboard-container.dark-theme .stat-card:hover {
  box-shadow: 0 8px 16px rgba(255, 255, 255, 0.1) !important;
}

/* Icon wrapper */
.stat-card__icon-wrapper {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  opacity: 0.8;
}

.stat-card--primary .stat-card__icon-wrapper {
  background-color: rgba(33, 150, 243, 0.1);
}

.stat-card--success .stat-card__icon-wrapper {
  background-color: rgba(76, 175, 80, 0.1);
}

.stat-card--info .stat-card__icon-wrapper {
  background-color: rgba(3, 169, 244, 0.1);
}

/* Content area */
.stat-card__content {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 100%;
}

.stat-card__title {
  font-size: 14px;
  color: #757575;
  margin-bottom: 8px;
  transition: color 0.3s ease;
}

.stat-card__value {
  font-size: 24px;
  font-weight: 700;
  color: #212121;
  transition: color 0.3s ease;
}

.stat-card__trend {
  margin-top: auto;
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
}

.stat-card__trend i {
  margin-right: 4px;
}

/* Card top border */
.stat-card:before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  height: 4px;
  width: 100%;
}

.stat-card--primary:before {
  background-color: #2196F3;
}

.stat-card--success:before {
  background-color: #4CAF50;
}

.stat-card--info:before {
  background-color: #03A9F4;
}

/* Responsive design */
@media (max-width: 768px) {
  .dashboard-container {
    padding: 16px;
  }
  
  .stat-card {
    height: 120px;
    padding: 16px;
  }
  
  .stat-card__value {
    font-size: 20px;
  }
}
</style>