<template>
  <v-app :dark="isDarkMode">
    <v-main>
      <div class="dashboard-wrapper" :class="{ 'dark-theme': isDarkMode }">
        <v-container class="dashboard-container">
          <!-- Hero Section -->
          <div class="hero-section">
            <div class="hero-content">
              <div class="brand-logo">
                <div class="brand-icon" :class="{ 'dark-logo': isDarkMode }">
                  <v-icon size="48" :color="isDarkMode ? 'white' : 'blue'">mdi-account-circle</v-icon>
                </div>
              </div>
              <h1 class="hero-title" :class="{ 'dark-text': isDarkMode }">Xush kelibsiz!</h1>
              <p class="hero-subtitle" :class="{ 'dark-text': isDarkMode }">Boshqaruv paneli</p>

              <!-- User Role and Name -->
              <div class="user-info mb-8">
                <v-chip large class="role-badge mr-4" :color="userRole === 'admin' ? 'red' : 'green'"
                  text-color="white">
                  <v-icon left>{{ userRole === 'admin' ? 'mdi-shield-crown' : 'mdi-account-tie' }}</v-icon>
                  {{ userRole === 'admin' ? 'Admin' : 'O\'qituvchi' }}
                </v-chip>
                <h2 class="user-name" :class="{ 'dark-text': isDarkMode }">{{ userName }}</h2>
              </div>

              <!-- Firebase Status Indicator -->
              <div class="firebase-status" v-if="firebaseUpdateStatus">
                <v-chip small :color="firebaseUpdateStatus === 'success' ? 'green' : 'orange'" text-color="white">
                  <v-icon left small>{{ firebaseUpdateStatus === 'success' ? 'mdi-check' : 'mdi-sync' }}</v-icon>
                  {{ firebaseUpdateStatus === 'success' ? 'Ma\'lumotlar yangilandi' : 'Yangilanmoqda...' }}
                </v-chip>
              </div>

              <!-- Debug Info (faqat development da) -->
              <div class="debug-info" v-if="showDebugInfo">
                <v-chip small color="info" text-color="white">
                  <v-icon left small>mdi-bug</v-icon>
                  Debug: {{ debugMessage }}
                </v-chip>
              </div>
            </div>
          </div>

          <!-- Stats Cards -->
          <div class="stats-section">
            <v-row>
              <!-- Today's Date Card -->
              <v-col cols="12" sm="6" md="3">
                <div class="glass-card" :class="isDarkMode ? 'dark-card' : 'light-card'">
                  <div class="card-glow"></div>
                  <div class="card-icon">
                    <v-icon size="48" :color="isDarkMode ? 'white' : 'blue'">mdi-calendar-today</v-icon>
                  </div>
                  <div class="card-value" :class="isDarkMode ? '' : 'dark-text'">
                    {{ formatDate(currentDate) }}
                  </div>
                  <div class="card-label" :class="isDarkMode ? '' : 'dark-label'">
                    Bugungi sana
                  </div>
                </div>
              </v-col>

              <!-- Current Time Card -->
              <v-col cols="12" sm="6" md="3">
                <div class="glass-card" :class="isDarkMode ? 'dark-card' : 'light-card'">
                  <div class="card-glow"></div>
                  <div class="card-icon">
                    <v-icon size="48" :color="isDarkMode ? 'white' : 'green'">mdi-clock-outline</v-icon>
                  </div>
                  <div class="card-value" :class="isDarkMode ? '' : 'dark-text'">
                    {{ formatTime(currentTime) }}
                  </div>
                  <div class="card-label" :class="isDarkMode ? '' : 'dark-label'">
                    Joriy vaqt
                  </div>
                </div>
              </v-col>

              <!-- Total Students Card -->
              <v-col cols="12" sm="6" md="3">
                <router-link to="/student" class="text-decoration-none">
                  <div class="glass-card" :class="isDarkMode ? 'dark-card' : 'light-card'">
                    <div class="card-glow"></div>
                    <div class="card-icon">
                      <v-icon size="48" :color="isDarkMode ? 'white' : 'purple'">mdi-account-group</v-icon>
                    </div>
                    <div class="card-value" :class="isDarkMode ? '' : 'dark-text'">
                      {{ totalStudents }}
                    </div>
                    <div class="card-label" :class="isDarkMode ? '' : 'dark-label'">
                      Jami O'quvchilar
                    </div>
                  </div>
                </router-link>
              </v-col>

              <!-- Total Payments Card -->
              <v-col cols="12" sm="6" md="3">
                <router-link to="/payment" class="no-underline text-decoration-none">
                  <div class="glass-card" :class="isDarkMode ? 'dark-card' : 'light-card'">
                    <div class="card-glow"></div>
                    <div class="card-icon">
                      <v-icon size="48" :color="isDarkMode ? 'white' : 'orange'">mdi-currency-usd</v-icon>
                    </div>
                    <div class="card-value" :class="isDarkMode ? '' : 'dark-text'">
                      {{ formatCurrency(totalPayments) }}
                    </div>
                    <div class="card-label" :class="isDarkMode ? '' : 'dark-label'">
                      Jami To'lovlar
                    </div>
                  </div>
                </router-link>
              </v-col>
            </v-row>
          </div>
        </v-container>
      </div>
    </v-main>
  </v-app>
</template>

<script>
import { db } from "@/firebaseConfig";
import { collection, getDocs, query, where, doc, updateDoc, setDoc, getDoc, onSnapshot } from "firebase/firestore";

export default {
  name: 'SignInDashboard',
  data() {
    return {
      isDarkMode: false,
      currentTime: new Date(),
      currentDate: new Date(),
      timeInterval: null,
      themeCheckInterval: null,
      userDataCheckInterval: null,
      firebaseUpdateInterval: null,
      lastTheme: null,
      lastUserName: null,
      lastUserRole: null,
      storageListener: null,
      currentUserId: null,
      firebaseUpdateStatus: null,
      updateTimeout: null,
      studentsListener: null,

      // Debug
      showDebugInfo: false,
      debugMessage: '',

      // User data
      userName: '',
      userRole: '',

      // Firebase data
      students: [],
      loading: false,
      
      // Previous values for comparison
      previousTotalStudents: 0,
      previousTotalPayments: 0,

      // Last Firebase update time
      lastFirebaseUpdate: null,
      firebaseUpdateCooldown: 3000, // 3 soniya
    }
  },
  computed: {
    // Calculate filtered students based on role
    filteredStudents() {
      if (!this.students || this.students.length === 0) return [];

      let filtered = this.students;

      // Filter by teacher if not admin
      if (this.userRole !== 'admin' && this.userName) {
        filtered = filtered.filter(student => {
          if (!student.teacher || !student.teacher.name) return false;
          return student.teacher.name.toLowerCase().trim() === this.userName.toLowerCase().trim();
        });
      }

      return filtered;
    },

    // Calculate total students
    totalStudents() {
      return this.filteredStudents.length;
    },

    // Calculate total payments
    totalPayments() {
      return this.filteredStudents.reduce((total, student) => {
        const parsedPayment = this.parsePayment(student.payment);
        return !isNaN(parsedPayment) ? total + parsedPayment : total;
      }, 0);
    }
  },
  watch: {
    // isDarkMode o'zgarsa avtomatik Vuetify theme ni yangilash
    isDarkMode(newValue) {
      this.$vuetify.theme.dark = newValue;
    },

    // userName o'zgarsa talabalarni qayta yuklash
    userName(newValue, oldValue) {
      if (newValue !== oldValue && newValue) {
        this.loadStudents();
      }
    },

    // userRole o'zgarsa talabalarni qayta yuklash
    userRole(newValue, oldValue) {
      if (newValue !== oldValue && newValue) {
        this.loadStudents();
      }
    },

    // totalStudents o'zgarsa Firebase ga yangilash
    totalStudents(newValue, oldValue) {
      if (newValue !== oldValue && this.canUpdateFirebase()) {
        this.debugMessage = `Students: ${oldValue} → ${newValue}`;
        this.scheduleFirebaseUpdate();
      }
    },

    // totalPayments o'zgarsa Firebase ga yangilash
    totalPayments(newValue, oldValue) {
      if (newValue !== oldValue && this.canUpdateFirebase()) {
        this.debugMessage = `Payments: ${oldValue} → ${newValue}`;
        this.scheduleFirebaseUpdate();
      }
    }
  },
  async mounted() {
    // Load theme from localStorage
    this.loadTheme();
    this.lastTheme = localStorage.getItem('theme');

    // Load user data
    await this.loadUserData();
    this.lastUserName = this.userName;
    this.lastUserRole = this.userRole;

    // Setup storage event listener
    this.setupStorageListener();

    // Setup polling intervals
    this.setupPollingIntervals();

    // Update time every second
    this.timeInterval = setInterval(() => {
      this.currentTime = new Date()
      this.currentDate = new Date()
    }, 1000)

    // Load students with real-time listener
    await this.loadStudentsWithListener();

    // Initial Firebase update
    setTimeout(() => {
      this.updateFirebaseStats();
    }, 2000);
  },
  beforeDestroy() {
    // Barcha intervallarni tozalash
    if (this.timeInterval) clearInterval(this.timeInterval);
    if (this.themeCheckInterval) clearInterval(this.themeCheckInterval);
    if (this.userDataCheckInterval) clearInterval(this.userDataCheckInterval);
    if (this.firebaseUpdateInterval) clearInterval(this.firebaseUpdateInterval);
    if (this.updateTimeout) clearTimeout(this.updateTimeout);

    // Firestore listener ni o'chirish
    if (this.studentsListener) {
      this.studentsListener();
    }

    // Storage listener ni o'chirish
    if (this.storageListener) {
      window.removeEventListener('storage', this.storageListener);
    }

    // Custom event listener ni o'chirish
    window.removeEventListener('themeChanged', this.handleThemeChanged);
    window.removeEventListener('userDataChanged', this.handleUserDataChanged);
  },
  methods: {
    // Firebase update qilish mumkinligini tekshirish
    canUpdateFirebase() {
      const now = Date.now();
      if (this.lastFirebaseUpdate && (now - this.lastFirebaseUpdate) < this.firebaseUpdateCooldown) {
        return false;
      }
      return this.userName;
    },

    // Firebase update ni rejalashtirish
    scheduleFirebaseUpdate() {
      if (this.updateTimeout) {
        clearTimeout(this.updateTimeout);
      }
      
      this.updateTimeout = setTimeout(() => {
        this.updateFirebaseStats();
      }, 1000); // 1 soniya kutish
    },

    // Theme yuklash
    loadTheme() {
      const savedTheme = localStorage.getItem('theme');
      if (savedTheme) {
        this.isDarkMode = savedTheme === 'dark';
      }
      this.$vuetify.theme.dark = this.isDarkMode;
    },

    // User ma'lumotlarini yuklash
    async loadUserData() {
      const teacherName = localStorage.getItem('teacherName');
      const userRole = localStorage.getItem('userRole');
      const userId = localStorage.getItem('userId') || localStorage.getItem('currentUserId');

      if (teacherName) {
        this.userName = teacherName;
      }

      if (userRole) {
        this.userRole = userRole;
      }

      if (userId) {
        this.currentUserId = userId;
      }

      console.log('User data loaded:', { userName: this.userName, userRole: this.userRole, userId: this.currentUserId });
    },

    // Firebase ga statistikalarni yangilash - users collection ichida
    async updateFirebaseStats() {
      if (!this.canUpdateFirebase()) {
        console.log('Firebase update skipped - conditions not met');
        return;
      }

      // Cooldown check
      const now = Date.now();
      if (this.lastFirebaseUpdate && (now - this.lastFirebaseUpdate) < this.firebaseUpdateCooldown) {
        console.log('Firebase update skipped - cooldown active');
        return;
      }

      try {
        this.firebaseUpdateStatus = 'updating';
        this.lastFirebaseUpdate = now;

        // users collection ichida foydalanuvchi hujjatiga yo'naltirish
        const userDocRef = doc(db, 'users', this.userName);
        
        // Hujjat mavjudligini tekshirish
        const docSnap = await getDoc(userDocRef);
        
        // Yangilanishi kerak bo'lgan ma'lumotlar
        const statsData = {
          totalStudents: this.totalStudents,
          totalPayments: this.totalPayments,
          lastStatsUpdate: new Date().toISOString(),
          updatedAt: new Date()
        };

        if (docSnap.exists()) {
          // Mavjud hujjatni yangilash - faqat stats ma'lumotlarini
          await updateDoc(userDocRef, statsData);
          console.log('User stats updated in Firebase');
        } else {
          // Agar hujjat mavjud bo'lmasa, yangi hujjat yaratish
          await setDoc(userDocRef, {
            name: this.userName,
            role: this.userRole,
            createdAt: new Date(),
            ...statsData
          });
          console.log('New user document created with stats');
        }

        // Oldingi qiymatlarni yangilash
        this.previousTotalStudents = this.totalStudents;
        this.previousTotalPayments = this.totalPayments;

        this.firebaseUpdateStatus = 'success';
        this.debugMessage = 'Firebase stats updated successfully';
        
        console.log('Firebase user stats updated:', {
          userName: this.userName,
          totalStudents: this.totalStudents,
          totalPayments: this.totalPayments,
          path: `users/${this.userName}`
        });

        // Statusni 3 soniyadan keyin tozalash
        setTimeout(() => {
          this.firebaseUpdateStatus = null;
        }, 3000);

      } catch (error) {
        console.error('Firebase stats update error:', error);
        this.firebaseUpdateStatus = null;
        this.debugMessage = 'Firebase stats update failed: ' + error.message;
        
        // Xatolik bo'lsa cooldown ni reset qilish
        this.lastFirebaseUpdate = null;
      }
    },

    // Storage event listener ni o'rnatish
    setupStorageListener() {
      this.storageListener = (event) => {
        console.log('Storage event:', event.key, event.newValue);

        if (event.key === 'theme') {
          this.isDarkMode = event.newValue === 'dark';
          this.lastTheme = event.newValue;
          this.$forceUpdate();
        }

        if (event.key === 'teacherName' && event.newValue !== this.userName) {
          this.userName = event.newValue || '';
          this.lastUserName = event.newValue;
        }

        if (event.key === 'userRole' && event.newValue !== this.userRole) {
          this.userRole = event.newValue || '';
          this.lastUserRole = event.newValue;
        }

        if (event.key === 'userId' || event.key === 'currentUserId') {
          this.currentUserId = event.newValue;
        }
      };

      window.addEventListener('storage', this.storageListener);
    },

    // Polling intervallarni o'rnatish
    setupPollingIntervals() {
      // Theme o'zgarishini tekshirish
      this.themeCheckInterval = setInterval(() => {
        this.checkThemeChange();
      }, 500);

      // User data o'zgarishini tekshirish
      this.userDataCheckInterval = setInterval(() => {
        this.checkUserDataChange();
      }, 1000);

      // Firebase periodic update
      this.firebaseUpdateInterval = setInterval(() => {
        if (this.hasStatsChanged()) {
          this.updateFirebaseStats();
        }
      }, 10000); // 10 soniyada bir tekshirish
    },

    // Statistikalar o'zgarganini tekshirish
    hasStatsChanged() {
      return this.totalStudents !== this.previousTotalStudents || 
             this.totalPayments !== this.previousTotalPayments;
    },

    // Theme o'zgarishini tekshirish
    checkThemeChange() {
      const currentTheme = localStorage.getItem('theme');
      if (currentTheme !== this.lastTheme) {
        this.lastTheme = currentTheme;
        this.isDarkMode = currentTheme === 'dark';
        this.$forceUpdate();
      }
    },

    // User data o'zgarishini tekshirish
    checkUserDataChange() {
      const currentUserName = localStorage.getItem('teacherName');
      const currentUserRole = localStorage.getItem('userRole');
      const currentUserId = localStorage.getItem('userId') || localStorage.getItem('currentUserId');

      if (currentUserName !== this.lastUserName) {
        this.lastUserName = currentUserName;
        this.userName = currentUserName || '';
      }

      if (currentUserRole !== this.lastUserRole) {
        this.lastUserRole = currentUserRole;
        this.userRole = currentUserRole || '';
      }

      if (currentUserId !== this.currentUserId) {
        this.currentUserId = currentUserId;
      }
    },

    // Custom event handlerlar
    handleThemeChanged(event) {
      this.isDarkMode = event.detail.isDark;
      this.$forceUpdate();
    },

    handleUserDataChanged(event) {
      if (event.detail.userName !== undefined) {
        this.userName = event.detail.userName;
      }
      if (event.detail.userRole !== undefined) {
        this.userRole = event.detail.userRole;
      }
    },

    // Talabalarni real-time listener bilan yuklash
    async loadStudentsWithListener() {
      if (!this.userName) {
        console.log('No username found, skipping students load');
        return;
      }

      this.loading = true;
      
      try {
        // Mavjud listener ni tozalash
        if (this.studentsListener) {
          this.studentsListener();
        }

        let studentQuery;

        if (this.userRole === 'admin') {
          studentQuery = collection(db, 'students');
        } else {
          studentQuery = query(
            collection(db, 'students'),
            where('teacher.name', '==', this.userName)
          );
        }

        // Real-time listener ni o'rnatish
        this.studentsListener = onSnapshot(studentQuery, (querySnapshot) => {
          const newStudents = querySnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data()
          }));

          // Ma'lumotlar haqiqatan o'zgarganini tekshirish
          const hasChanged = newStudents.length !== this.students.length ||
                           JSON.stringify(newStudents) !== JSON.stringify(this.students);

          if (hasChanged) {
            this.students = newStudents;
            console.log('Students updated via listener:', this.students.length);
            
            // Qisqa vaqt kutib Firebase stats ni yangilash
            setTimeout(() => {
              this.updateFirebaseStats();
            }, 500);
          }
        }, (error) => {
          console.error('Students listener error:', error);
          this.students = [];
        });

        this.loading = false;
      } catch (error) {
        console.error('Error setting up students listener:', error);
        this.students = [];
        this.loading = false;
      }
    },

    // Fallback: Talabalarni bir marta yuklash
    async loadStudents() {
      if (!this.userName) {
        console.log('No username found, skipping students load');
        return;
      }

      this.loading = true;
      try {
        let studentQuery;

        if (this.userRole === 'admin') {
          studentQuery = collection(db, 'students');
        } else {
          studentQuery = query(
            collection(db, 'students'),
            where('teacher.name', '==', this.userName)
          );
        }

        const querySnapshot = await getDocs(studentQuery);
        this.students = querySnapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));

        console.log('Students loaded:', this.students.length);
        
        // Oldingi qiymatlarni boshlang'ich qiymatlar bilan to'ldirish
        this.previousTotalStudents = this.totalStudents;
        this.previousTotalPayments = this.totalPayments;
        
      } catch (error) {
        console.error('Error fetching students:', error);
        this.students = [];
      } finally {
        this.loading = false;
      }
    },

    // Turli formatdagi to'lovlarni parse qilish
    parsePayment(payment) {
      if (!payment) return 0;

      let paymentValue = payment;
      if (typeof paymentValue !== 'string') {
        paymentValue = String(paymentValue);
      }
      return parseFloat(paymentValue.replace(/[^\d.-]/g, '')) || 0;
    },

    // Sanani formatlash
    formatDate(date) {
      return date.toLocaleDateString('uz-UZ', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    },

    // Vaqtni formatlash
    formatTime(date) {
      return date.toLocaleTimeString('uz-UZ', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    },

    // Valyutani formatlash - so'mda ko'rsatish
    formatCurrency(value) {
      if (value === undefined || value === null || isNaN(value)) return "0 so'm";

      const numValue = parseFloat(value);
      return new Intl.NumberFormat('uz-UZ').format(numValue) + " so'm";
    }
  }
}
</script>

<style scoped>
.v-app {
  transition: all 0.3s ease;
}

.theme-toggle {
  margin: 16px !important;
  z-index: 1000 !important;
  transition: all 0.3s ease;
}

.theme-toggle:hover {
  transform: scale(1.1);
}

.dashboard-wrapper {
  min-height: 100vh;
  background: linear-gradient(135deg, #f1f1f1 0%, #ffffff 100%);
  transition: all 0.5s ease;
}

.dashboard-wrapper.dark-theme {
  background: linear-gradient(135deg, #202124 0%, #202124 100%);
}

/* Dashboard Container */
.dashboard-container {
  position: relative;
  z-index: 1;
  padding: 40px 20px;
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: 60px 0;
  margin-bottom: 60px;
}

.hero-content {
  max-width: 600px;
  margin: 0 auto;
}

.brand-logo {
  margin-bottom: 30px;
}

.brand-icon {
  background: rgba(162, 195, 241, 0.269);
  border-radius: 20px;
  padding: 20px;
  backdrop-filter: blur(10px);
  border: 2px solid rgba(255, 255, 255, 0.3);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.brand-icon.dark-logo {
  background: rgba(255, 255, 255, 0.2);
}

.hero-title {
  font-size: 4rem;
  font-weight: 900;
  color: #222;
  margin-bottom: 16px;
  text-shadow: 0 4px 20px rgba(68, 68, 68, 0.3);
  letter-spacing: -2px;
}

.hero-title.dark-text,
.hero-subtitle.dark-text,
.user-name.dark-text {
  color: white;
  text-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.hero-subtitle {
  font-size: 1.4rem;
  color: rgba(45, 43, 43, 0.9);
  margin-bottom: 30px;
  font-weight: 300;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.user-name {
  font-size: 2rem;
  font-weight: 700;
  color: #222;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.role-badge {
  background: rgba(255, 255, 255, 0.2) !important;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

/* Firebase Status */
.firebase-status {
  margin-top: 16px;
}

/* Glass Stats Cards */
.stats-section {
  margin-bottom: 60px;
}

.glass-card {
  position: relative;
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 30px;
  text-align: center;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  cursor: pointer;
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

/* Dark theme cards */
.glass-card.dark-card {
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.glass-card.dark-card:hover {
  background: rgba(255, 255, 255, 0.25);
  transform: translateY(-10px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

/* Light theme cards */
.glass-card.light-card {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.glass-card.light-card:hover {
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-10px) scale(1.02);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.glass-card .card-icon {
  margin-bottom: 15px;
}

.glass-card .card-value {
  font-size: 2rem;
  font-weight: 900;
  color: white;
  margin-bottom: 8px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.glass-card .card-label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}

/* Light theme text */
.glass-card .card-value.dark-text {
  color: #2c3e50;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.glass-card .card-label.dark-label {
  color: #546e7a;
}

.glass-card .card-glow {
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: rotate 20s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Responsive Design */
@media (max-width: 960px) {
  .hero-title {
    font-size: 3rem;
  }

  .glass-card .card-value {
    font-size: 1.8rem;
  }

  .glass-card {
    height: 180px;
  }
}

@media (max-width: 600px) {
  .hero-title {
    font-size: 2.5rem;
  }

  .hero-subtitle {
    font-size: 1.2rem;
  }

  .user-name {
    font-size: 1.5rem;
  }

  .dashboard-container {
    padding: 20px 10px;
  }

  .glass-card {
    height: 160px;
    padding: 20px;
  }

  .glass-card .card-value {
    font-size: 1.5rem;
  }

  .glass-card .card-label {
    font-size: 0.8rem;
  }

  .user-info {
    flex-direction: column;
    gap: 12px;
  }
}
</style>