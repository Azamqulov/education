<template>
  <v-card class="pa-4">
    <v-card-title class="text-h5 text-center mb-4">
      O'qituvchilar Statistikasi
    </v-card-title>

    <!-- Loading -->
    <div v-if="loading" class="text-center py-8">
      <v-progress-circular indeterminate color="primary" size="40"></v-progress-circular>
      <p class="mt-3">Yuklanmoqda...</p>
    </div>

    <!-- Teachers List -->
    <div v-else class="teacher-list" >
      <transition-group name="fade-slide" tag="div" class="teacher-list mt-2">
        <div
          v-for="(teacher, index) in teachers"
          :key="teacher.id"
          class="teacher-item" 
          :class="{ 'dark-theme': isDarkMode }"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <div class="teacher-info">
            <div class="teacher-details">
              <h3 class="teacher-name">{{ teacher.name }}</h3>
              <div class="teacher-stats">
                <div class="stat-item">
                  <v-icon small class="mr-1">mdi-account-group</v-icon>
                  <span>{{ teacher.totalStudents }} ta talaba</span>
                </div>
                <div class="stat-item">
                  <v-icon small class="mr-1">mdi-currency-usd</v-icon>
                  <span>{{ formatCurrency(teacher.totalPayments) }} so'm</span>
                </div>
              </div>
            </div>
            <div class="teacher-avatar">
              <v-avatar color="primary" size="48">
                <span class="white--text text-h6">{{ getInitials(teacher.name) }}</span>
              </v-avatar>
            </div>
          </div>
        </div>
      </transition-group>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && teachers.length === 0" class="text-center py-8">
      <v-icon size="64" color="grey lighten-1" class="mb-4">mdi-account-search</v-icon>
      <p class="text-h6 grey--text">Hech qanday o'qituvchi topilmadi</p>
    </div>
  </v-card>
</template>

<script>
import { collection, getDocs, query, where } from "firebase/firestore";
import { db } from "@/firebaseConfig";

export default {
  name: "TeachersStatistics",
  
  data() {
    return {
      // Theme management
      isDarkMode: false,
      themeCheckInterval: null,
      lastTheme: null,
      storageListener: null,

      teachers: [],
      loading: true,
    };
  },

  computed: {
    // You can add computed properties for theme-related styling if needed
  },

  watch: {
    isDarkMode: {
      handler(newValue) {
        this.$vuetify.theme.dark = newValue;
      },
      immediate: true,
    },
  },

  async created() {
    await this.initializeComponent();
  },

  async mounted() {
    this.loadTheme();
    this.setupEventListeners();
    this.setupPollingIntervals();
  },

  beforeDestroy() {
    this.cleanup();
  },

  methods: {
    async initializeComponent() {
      try {
        this.loading = true;
        await this.fetchTeachers();
      } catch (error) {
        console.error("Initialization error:", error);
      } finally {
        this.loading = false;
      }
    },

    // Theme management methods
    loadTheme() {
      const savedTheme = localStorage.getItem("theme");
      this.isDarkMode = savedTheme === "dark";
      this.lastTheme = savedTheme;
      this.$vuetify.theme.dark = this.isDarkMode;
    },

    setupEventListeners() {
      this.storageListener = (event) => {
        if (event.key === "theme") {
          this.isDarkMode = event.newValue === "dark";
          this.lastTheme = event.newValue;
        }
      };

      window.addEventListener("storage", this.storageListener);
      window.addEventListener("themeChanged", this.handleThemeChanged);
    },

    setupPollingIntervals() {
      this.themeCheckInterval = setInterval(() => {
        this.checkThemeChange();
      }, 1000);
    },

    checkThemeChange() {
      const currentTheme = localStorage.getItem("theme");
      if (currentTheme !== this.lastTheme) {
        this.lastTheme = currentTheme;
        this.isDarkMode = currentTheme === "dark";
      }
    },

    handleThemeChanged(event) {
      this.isDarkMode = event.detail.theme === "dark";
    },

    cleanup() {
      if (this.themeCheckInterval) {
        clearInterval(this.themeCheckInterval);
      }

      if (this.storageListener) {
        window.removeEventListener("storage", this.storageListener);
      }

      window.removeEventListener("themeChanged", this.handleThemeChanged);
    },

    // Original methods
    async fetchTeachers() {
      try {
        this.loading = true;
        const querySnapshot = await getDocs(collection(db, "users"));
        
        const allTeachers = await Promise.all(
          querySnapshot.docs.map(async (doc) => {
            const teacherData = doc.data();
            
            // Skip if user is admin
            if (teacherData.role === 'admin') {
              return null;
            }
            
            // Fetch students for this teacher
            const studentsQuery = query(
              collection(db, "students"),
              where("teacher", "==", doc.id)
            );
            const studentsSnapshot = await getDocs(studentsQuery);
            
            const students = studentsSnapshot.docs.map((studentDoc) => ({
              id: studentDoc.id,
              ...studentDoc.data()
            }));

            // Calculate total payments from students
            const totalPayments = students.reduce((total, student) => {
              let paymentValue = student.payment || 0;
              if (typeof paymentValue === "string") {
                paymentValue = paymentValue.replace(/[^\d.-]/g, "");
              }
              const parsedPayment = parseFloat(paymentValue);
              return !isNaN(parsedPayment) ? total + parsedPayment : total;
            }, 0);

            return {
              id: doc.id,
              name: teacherData.name || "Noma'lum",
              totalPayments: totalPayments,
              totalStudents: students.length,
              ...teacherData
            };
          })
        );
        
        // Filter out null values (admins)
        this.teachers = allTeachers.filter(teacher => teacher !== null);
      } catch (error) {
        console.error("O'qituvchilarni yuklashda xatolik:", error);
      } finally {
        this.loading = false;
      }
    },

    formatCurrency(value) {
      return new Intl.NumberFormat('uz-UZ').format(value || 0);
    },

    getInitials(name) {
      if (!name) return "?";
      const words = name.split(' ');
      if (words.length === 1) {
        return words[0].charAt(0).toUpperCase();
      }
      return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
    }
  }
};
</script>

<style scoped>
.teacher-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.teacher-item {
  padding: 20px;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  background-color: #fafafa;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: fadeInUp 0.6s ease-out forwards;
  opacity: 0;
  transform: translateY(20px);
}
.teacher-item.dark-theme {
  color: #ffffff;
  background-color: #0d111785;
}
.teacher-item:hover {
  border-color: #1976d2;
  background-color: #f5f5f5;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.teacher-item.dark-theme:hover {
    border-color: #1976d2;
  background-color: #211e1e31;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.teacher-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.teacher-details {
  flex: 1;
}

.teacher-name {
  margin: 0 0 8px 0;
  font-size: 1.4rem;
  font-weight: 600;
  color: #2c3e50;
}

.teacher-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-item {
  display: flex;
  align-items: center;
  color: #666;
  font-size: 1rem;
  transition: color 0.2s ease;
}

.teacher-item:hover .stat-item {
  color: #1976d2;
}

.teacher-avatar {
  flex-shrink: 0;
}

/* Animations */
@keyframes fadeInUp {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.5s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(-30px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

.fade-slide-move {
  transition: transform 0.5s ease;
}

/* Dark theme */
.v-application.theme--dark .teacher-item {
  border-color: #424242;
  background-color: #1e1e1e;
}

.v-application.theme--dark .teacher-item:hover {
  border-color: #2196f3;
  background-color: #2d2d2d;
}

.v-application.theme--dark .teacher-name {
  color: #ffffff;
}

.v-application.theme--dark .stat-item {
  color: #bbb;
}

.v-application.theme--dark .teacher-item:hover .stat-item {
  color: #2196f3;
}

/* Mobile responsive */
@media (max-width: 600px) {
  .teacher-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .teacher-stats {
    width: 100%;
  }
  
  .stat-item {
    font-size: 0.8rem;
  }
  
  .teacher-item {
    padding: 16px;
  }
}

/* Loading animation for progress circular */
.v-progress-circular {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}
</style>