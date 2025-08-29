<template>
  <div class="modern-dashboard" :class="{ 'dark-theme': isDarkMode }">
    <!-- Main Content -->
    <v-container fluid class="pa-6">
      <!-- Header with Glass Effect -->
      <div class="glass-header mb-8" :class="{ 'dark-header': isDarkMode }">
        <div class="header-content">
          <div class="title-section">
            <div class="icon-wrapper">
              <v-icon size="32" color="white">mdi-account-group</v-icon>
            </div>
            <div>
              <h1 class="main-title">O'quvchilar Dashboardi</h1>
              <p class="subtitle">Ta'lim markazidagi barcha ma'lumotlar</p>
            </div>
          </div>

          <div class="stats-cards">
            <div class="stat-card">
              <div class="stat-number">{{ filteredStudents.length }}</div>
              <div class="stat-label">O'quvchilar</div>
            </div>
            <div class="stat-card">
              <div class="stat-number">{{ subjects.length }}</div>
              <div class="stat-label">Fanlar</div>
            </div>
          </div>
        </div>

        <div class="action-buttons">
          <button class="modern-btn primary" @click="openAddModal">
            <v-icon left>mdi-plus-circle</v-icon>
            Yangi O'quvchi
          </button>
          <button class="modern-btn secondary" @click="exportToExcel">
            <v-icon left>mdi-download</v-icon>
            Excel Export
          </button>
        </div>
      </div>

      <!-- Admin Filter Section - Faqat admin uchun -->
      <div v-if="isAdmin" class="admin-filter-section mb-6">
        <v-card class="filter-card" elevation="2">
          <v-card-title class="filter-title">
            <v-icon left color="blue">mdi-filter-variant</v-icon>
            Filter Panel
          </v-card-title>
          <v-card-text>
            <v-row>
              <!-- Qidiruv input -->
              <v-col cols="12" md="4">
                <v-text-field v-model="search" prepend-inner-icon="mdi-magnify"
                  label="Ism yoki Familya bo'yicha qidirish" outlined dense clearable
                  @input="onSearchInput"></v-text-field>
              </v-col>

              <!-- Fan bo'yicha filter -->
              <v-col cols="12" md="4">
                <v-select v-model="selectedSubject" :items="subjects" label="Fan bo'yicha filter" outlined dense
                  clearable prepend-inner-icon="mdi-book-open-variant"></v-select>
              </v-col>

              <!-- O'qituvchi bo'yicha filter -->
              <v-col cols="12" md="4">
                <v-select v-model="selectedTeacher" :items="teachers" label="O'qituvchi bo'yicha filter" outlined dense
                  clearable prepend-inner-icon="mdi-account-tie"></v-select>
              </v-col>


            </v-row>

            <!-- Qo'shimcha filter tugmalari -->
            <v-row class="mt-2">
              <v-col cols="12">
                <div class="filter-actions">
                  <v-btn small color="blue" outlined @click="clearAllFilters" class="mr-2">
                    <v-icon left small>mdi-filter-remove</v-icon>
                    Barcha filtrlarni tozalash
                  </v-btn>

                  <v-chip v-if="search" small close color="primary" class="mr-1" @click:close="search = ''">
                    Qidiruv: {{ search }}
                  </v-chip>

                  <v-chip v-if="selectedSubject" small close color="green" class="mr-1"
                    @click:close="selectedSubject = null">
                    Fan: {{ selectedSubject }}
                  </v-chip>

                  <v-chip v-if="selectedTeacher" small close color="indigo" class="mr-1"
                    @click:close="selectedTeacher = null">
                    O'qituvchi: {{ selectedTeacher }}
                  </v-chip>

                  <v-chip v-if="selectedPaymentRange" small close color="orange" class="mr-1"
                    @click:close="selectedPaymentRange = null">
                    To'lov: {{ getPaymentRangeLabel(selectedPaymentRange) }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </div>

      <!-- Pagination -->
      <div class="pagination-wrapper" v-if="!loading && filteredStudents.length > itemsPerPage">
        <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">
          <v-icon>mdi-chevron-left</v-icon>
        </button>

        <div class="page-numbers">
          <span class="page-info"> {{ currentPage }} / {{ totalPages }} </span>
        </div>

        <button class="page-btn" :disabled="currentPage === totalPages" @click="currentPage++">
          <v-icon>mdi-chevron-right</v-icon>
        </button>
      </div>
    </v-container>

    <v-container fluid>
      <!-- Students Data Table with Enhanced UI -->
      <v-card class="rounded-lg table-card" elevation="3">
        <v-data-table  :headers="headers" :items="filteredStudents" :items-per-page="10" :dense="denseTable === 1"
          :loading="loading" class="elevation-0 text-capitalize" :footer-props="{
            'items-per-page-options': [5, 10, 15, 20],
            'items-per-page-text': 'Sahifada:',
          }" :sort-by="['surname']" :sort-desc="[false]" multi-sort>
          <!-- Custom loading -->
          <template v-slot:loading>
            <div class="d-flex justify-center align-center pa-4">
              <v-progress-circular indeterminate color="blue" size="64"></v-progress-circular>
            </div>
          </template>

          <!-- Index column -->
          <template v-slot:item.index="{ index }">
            <v-chip x-small color="blue" text-color="white" class="font-weight-bold">
              {{ index + 1 }}
            </v-chip>
          </template>

          <!-- Name column -->
          <template v-slot:item.name="{ item }">
            <div class="d-flex align-center">
              <v-avatar size="32" color="blue lighten-4" class="mr-2">
                <span class="blue--text font-weight-bold text-capitalize">{{
                  getInitials(item.name)
                }}</span>
              </v-avatar>
              <span class="font-weight-medium text-capitalize">{{ item.name }}</span>
            </div>
          </template>

          <!-- Teacher column -->
          <template v-slot:item.teacher="{ item }">
            <div class="d-flex align-center">
              <v-avatar size="28" color="indigo lighten-1" class="mr-2">
                <span class="white--text">{{
                  getInitials(item.teacher.name)
                }}</span>
              </v-avatar>
              <span>{{ item.teacher.name }}</span>
            </div>
          </template>

          <!-- Subject column -->
          <template v-slot:item.subject="{ item }">
            <v-chip small :color="getSubjectColor(item.subject)" text-color="white" class="font-weight-medium">
              {{ item.subject }}
            </v-chip>
          </template>

          <!-- Phone column -->
          <template v-slot:item.phone="{ item }">
            <div class="d-flex align-center">
              <v-icon small color="grey" class="mr-1">mdi-phone</v-icon>
              {{ formatPhone(item.phone) }}
            </div>
          </template>

          <!-- Date column -->
          <template v-slot:item.date="{ item }">
            <div class="d-flex align-center">
              <v-icon small color="grey" class="mr-1">mdi-calendar</v-icon>
              {{ formatDate(item.date) }}
            </div>
          </template>

          <!-- Payment column -->
          <template v-slot:item.payment="{ item }">
            <span class="font-weight-bold" :class="getPaymentColor(item.payment)">
              {{ formatCurrency(item.payment) }}
            </span>
          </template>

          <!-- Actions column -->
          <template v-slot:item.actions="{ item }">
            <div class="d-flex">
              <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn fab x-small color="blue" class="mr-2 elevation-2" v-bind="attrs" v-on="on"
                    @click="editStudent(item)">
                    <v-icon>mdi-pencil</v-icon>
                  </v-btn>
                </template>
                <span>Tahrirlash</span>
              </v-tooltip>

              <v-tooltip bottom>
                <template v-slot:activator="{ on, attrs }">
                  <v-btn fab x-small color="error" class="elevation-2" v-bind="attrs" v-on="on"
                    @click="confirmDelete(item)">
                    <v-icon>mdi-delete</v-icon>
                  </v-btn>
                </template>
                <span>O'chirish</span>
              </v-tooltip>
            </div>
          </template>

          <!-- Empty state -->
          <template v-slot:no-data>
            <div class="pa-6 text-center empty-state">
              <v-icon size="64" color="grey lighten-1">mdi-account-search</v-icon>
              <h3 class="text-subtitle-1 font-weight-medium grey--text mt-3">
                O'quvchilar topilmadi
              </h3>
              <v-btn color="blue" class="mt-3" rounded @click="openAddModal">
                <v-icon left>mdi-account-plus</v-icon>
                O'quvchi qo'shish
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card>
    </v-container>

    <!-- Student Modal Component -->
    <student-modal :add-modal="addModal" :edit-modal="editModal" :delete-dialog="deleteDialog" :new-student="newStudent"
      :edited-student="editedStudent" :student-to-delete="studentToDelete" :subjects="subjects" :teachers="teachers"
      @close-add-modal="addModal = false" @close-edit-modal="editModal = false"
      @close-delete-modal="deleteDialog = false" @add-student="addStudent" @update-student="updateStudent"
      @confirm-delete="confirmDeleteStudent" />
  </div>
</template>

<script>
import Toastify from "toastify-js";
import { db } from "@/firebaseConfig";
import {
  collection,
  getDocs,
  addDoc,
  deleteDoc,
  updateDoc,
  doc,
} from "firebase/firestore";
import * as XLSX from "xlsx";
import StudentModal from "./StudentModal.vue";

export default {
  name: "StudentManager",
  components: {
    StudentModal,
  },
  data() {
    return {
      isDarkMode: false,
      themeCheckInterval: null,
      userDataCheckInterval: null,
      lastTheme: null,
      storageListener: null,
      search: "",
      selectedSubject: null,
      selectedTeacher: null,
      selectedPaymentRange: null,
      currentUser: null,
      role: "teacher",
      loading: true,
      denseTable: 0,
      headers: [
        { text: "№", value: "index", sortable: false, width: "40px" },
        { text: "Familya", value: "surname", class: "text-capitalize surname" },
        { text: "Ism", value: "name" },
        { text: "O'qituvchi", value: "teacher.name" },
        { text: "Fan", value: "subject" },
        { text: "Sana", value: "date" },
        { text: "Telefon", value: "phone" },
        { text: "To'lov", value: "payment" },
        {
          text: "Amallar",
          value: "actions",
          sortable: false,
          align: "center",
          width: "100px",
          class: "text-capitalize",
        },
      ],
      students: [],
      subjects: [],
      teachers: [],
      paymentRanges: [
        { text: "0 - 200,000", value: "0-200000" },
        { text: "200,000 - 500,000", value: "200000-500000" },
        { text: "500,000 - 1,000,000", value: "500000-1000000" },
        { text: "1,000,000+", value: "1000000+" },
      ],
      newStudent: {
        name: "",
        surname: "",
        phone: "",
        subject: "",
        teacher: "",
        payment: "",
        date: new Date().toISOString().substr(0, 10),
      },
      editedStudent: {
        name: "",
        surname: "",
        phone: "",
        subject: "",
        teacher: "",
        payment: "",
        date: "",
      },
      studentToDelete: null,
      addModal: false,
      editModal: false,
      deleteDialog: false,
      subjectColors: {
        Matematika: "blue",
        Fizika: "indigo",
        Kimyo: "deep-purple",
        Biologiya: "green",
        "Ingliz tili": "cyan darken-1",
        "Rus tili": "red lighten-1",
        Informatika: "teal",
      },
      lastSubject: "",
    };
  },

  computed: {
    isAdmin() {
      return this.role === "admin";
    },

    filteredStudents() {
      let filtered = [...this.students];

      // Search filter
      if (this.search) {
        const searchLower = this.search.toLowerCase().trim();
        filtered = filtered.filter((student) => {
          const name = student.name?.toLowerCase() || "";
          const surname = student.surname?.toLowerCase() || "";
          const phone = student.phone?.toString().toLowerCase() || "";
          return name.includes(searchLower) ||
            surname.includes(searchLower) ||
            phone.includes(searchLower);
        });
      }

      // Admin filters
      if (this.isAdmin) {
        if (this.selectedSubject) {
          filtered = filtered.filter(
            (student) => student.subject === this.selectedSubject
          );
        }

        if (this.selectedTeacher) {
          filtered = filtered.filter(
            (student) =>
              student.teacher?.name === this.selectedTeacher
          );
        }

        if (this.selectedPaymentRange) {
          filtered = filtered.filter((student) => {
            const payment = parseInt(student.payment) || 0;
            return this.isPaymentInRange(payment, this.selectedPaymentRange);
          });
        }
      } else {
        // Teacher filter - only show own students
        filtered = filtered.filter(
          (student) => student.teacher?.name === this.currentUser
        );
      }

      return filtered;
    },
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
        this.currentUser = localStorage.getItem("teacherName");
        this.role = localStorage.getItem("userRole") || "teacher";

        if (!this.currentUser) {
          throw new Error("No teacher logged in");
        }

        this.loading = true;
        await Promise.all([
          this.loadStudents(),
          this.loadSubjects(),
          this.loadTeachers(),
        ]);

      } catch (error) {
        console.error("Initialization error:", error);
        this.showNotification(
          error.message === "No teacher logged in"
            ? "Tizimga kirilmagan. Iltimos qayta kiring!"
            : "Boshlang'ich ma'lumotlarni yuklashda xatolik",
          "error"
        );
      } finally {
        this.loading = false;
      }
    },

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
      }, 1000); // Reduced frequency for better performance
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

      if (this.userDataCheckInterval) {
        clearInterval(this.userDataCheckInterval);
      }

      if (this.storageListener) {
        window.removeEventListener("storage", this.storageListener);
      }

      window.removeEventListener("themeChanged", this.handleThemeChanged);
    },

    // Utility methods
    getInitials(name) {
      if (!name) return "?";
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase();
    },

    formatPhone(phone) {
      if (!phone) return "";
      const numbers = phone.toString().replace(/\D/g, "");

      if (numbers.length === 9) {
        return numbers.replace(/(\d{2})(\d{3})(\d{2})(\d{2})/, "($1) $2-$3-$4");
      } else if (numbers.length === 12) {
        return numbers.replace(
          /(\d{3})(\d{2})(\d{3})(\d{2})(\d{2})/,
          "+$1 ($2) $3-$4-$5"
        );
      }
      return phone;
    },

    formatDate(dateString) {
      if (!dateString) return "";
      try {
        const options = {
          year: "numeric",
          month: "2-digit",
          day: "2-digit"
        };
        return new Date(dateString).toLocaleDateString("uz-UZ", options);
      } catch (error) {
        return dateString;
      }
    },

    formatCurrency(value) {
      if (!value) return "0 so'm";
      const numValue = typeof value === 'string' ? parseInt(value) : value;
      return new Intl.NumberFormat('uz-UZ').format(numValue) + " so'm";
    },

    getPaymentColor(payment) {
      const amount = parseInt(payment) || 0;
      if (amount > 500000) return "green--text";
      if (amount > 300000) return "blue--text";
      if (amount > 0) return "orange--text";
      return "grey--text";
    },

    getSubjectColor(subject) {
      if (this.subjectColors[subject]) {
        return this.subjectColors[subject];
      }

      const colors = [
        "blue", "indigo", "deep-purple", "teal",
        "green", "orange", "red", "cyan"
      ];
      const hash = subject
        .split("")
        .reduce((acc, char) => acc + char.charCodeAt(0), 0);
      return colors[hash % colors.length];
    },

    // Filter methods
    clearAllFilters() {
      this.search = "";
      this.selectedSubject = null;
      this.selectedTeacher = null;
      this.selectedPaymentRange = null;
      this.showNotification("Barcha filtrlar tozalandi", "info");
    },

    isPaymentInRange(payment, range) {
      const [min, max] = range.split("-").map(Number);
      if (range.includes("+")) {
        return payment >= min;
      }
      return payment >= min && payment <= max;
    },

    getPaymentRangeLabel(range) {
      if (!range) return "";
      const rangeObj = this.paymentRanges.find((r) => r.value === range);
      return rangeObj ? rangeObj.text : "";
    },

    // Data loading methods
    async loadStudents() {
      try {
        const querySnapshot = await getDocs(collection(db, "students"));
        this.students = querySnapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
        }));
      } catch (error) {
        console.error("Error loading students:", error);
        this.showNotification(
          "O'quvchilar ma'lumotlarini yuklashda xatolik",
          "error"
        );
      }
    },

    async loadSubjects() {
      try {
        const querySnapshot = await getDocs(collection(db, "subjects"));
        this.subjects = querySnapshot.docs.map((doc) => doc.data().name);
      } catch (error) {
        console.error("Error loading subjects:", error);
        this.showNotification("Fanlarni yuklashda xatolik", "error");
      }
    },

    async loadTeachers() {
      try {
        const querySnapshot = await getDocs(collection(db, "teachers"));
        this.teachers = querySnapshot.docs.map((doc) => doc.data().name);
      } catch (error) {
        console.error("Error loading teachers:", error);
        this.showNotification("O'qituvchilarni yuklashda xatolik", "error");
      }
    },

    // CRUD operations
    openAddModal() {
      this.newStudent = {
        name: "",
        surname: "",
        phone: "",
        subject: "",
        teacher: this.isAdmin ? "" : this.currentUser,
        payment: "",
        date: new Date().toISOString().substr(0, 10),
      };
      this.addModal = true;
    },

    async addStudent(student) {
      try {
        this.loading = true;
        const payments = Array(12).fill(false);

        const docRef = await addDoc(collection(db, "students"), {
          ...student,
          teacher: { name: student.teacher },
          payments: payments,
        });

        this.students.push({
          ...student,
          id: docRef.id,
          teacher: { name: student.teacher },
          payments: payments,
        });

        this.showNotification("O'quvchi muvaffaqiyatli qo'shildi", "success");
        this.addModal = false;

      } catch (error) {
        console.error("Error adding student:", error);
        this.showNotification("O'quvchi qo'shishda xatolik yuz berdi", "error");
      } finally {
        this.loading = false;
      }
    },

    editStudent(student) {
      this.editedStudent = {
        ...student,
        teacher: student.teacher?.name || "",
      };
      this.editModal = true;
    },

    async updateStudent(student) {
      try {
        this.loading = true;
        const studentRef = doc(db, "students", student.id);

        const updateData = {
          name: student.name,
          surname: student.surname,
          phone: student.phone,
          subject: student.subject,
          teacher: { name: student.teacher },
          payment: student.payment,
          date: student.date,
        };

        await updateDoc(studentRef, updateData);

        const index = this.students.findIndex((s) => s.id === student.id);
        if (index !== -1) {
          this.students.splice(index, 1, {
            ...student,
            teacher: { name: student.teacher },
          });
        }

        this.showNotification(
          "O'quvchi ma'lumotlari muvaffaqiyatli yangilandi",
          "success"
        );
        this.editModal = false;

      } catch (error) {
        console.error("Error updating student:", error);
        this.showNotification(
          "O'quvchi ma'lumotlarini yangilashda xatolik",
          "error"
        );
      } finally {
        this.loading = false;
      }
    },

    confirmDelete(student) {
      this.studentToDelete = student;
      this.deleteDialog = true;
    },

    async confirmDeleteStudent() {
      if (!this.studentToDelete) return;

      try {
        this.loading = true;
        await deleteDoc(doc(db, "students", this.studentToDelete.id));

        const index = this.students.findIndex(
          (s) => s.id === this.studentToDelete.id
        );
        if (index > -1) {
          this.students.splice(index, 1);
        }

        this.showNotification("O'quvchi muvaffaqiyatli o'chirildi", "info");
        this.deleteDialog = false;
        this.studentToDelete = null;

      } catch (error) {
        console.error("Error deleting student:", error);
        this.showNotification(
          "O'quvchi o'chirishda xatolik yuz berdi",
          "error"
        );
      } finally {
        this.loading = false;
      }
    },

    // Export functionality
    exportToExcel() {
      try {
        this.loading = true;

        const exportData = this.filteredStudents.map((student, index) => ({
          "№": index + 1,
          "Ism": student.name,
          "Familya": student.surname,
          "Fan": student.subject,
          "O'qituvchi": student.teacher?.name || "",
          "Sana": this.formatDate(student.date),
          "Telefon": this.formatPhone(student.phone),
          "To'lov": this.formatCurrency(student.payment),
        }));

        const ws = XLSX.utils.json_to_sheet(exportData);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "O'quvchilar");

        const wscols = [
          { wch: 5 }, { wch: 15 }, { wch: 15 }, { wch: 15 },
          { wch: 15 }, { wch: 12 }, { wch: 15 }, { wch: 15 },
        ];
        ws["!cols"] = wscols;

        XLSX.utils.sheet_add_aoa(
          ws,
          [
            ["O'QUVCHILAR RO'YXATI"],
            [`Sana: ${new Date().toLocaleDateString("uz-UZ")}`],
            [""],
          ],
          { origin: "A1" }
        );

        const fileName = `o'quvchilar_ro'yxati_${new Date().toISOString().split('T')[0]}.xlsx`;
        XLSX.writeFile(wb, fileName);

        this.showNotification("Excel fayli muvaffaqiyatli yuklandi", "success");

      } catch (error) {
        console.error("Error exporting to Excel:", error);
        this.showNotification("Excel faylini yuklashda xatolik", "error");
      } finally {
        this.loading = false;
      }
    },

    // Notification system
    showNotification(message, type = "success") {
      try {
        if (typeof Toastify === "function") {
          const bgColors = {
            success: "linear-gradient(to right, #4CAF50, #2196F3)",
            error: "linear-gradient(to right, #f44336, #e91e63)",
            info: "linear-gradient(to right, #2196F3, #03A9F4)",
          };

          Toastify({
            text: message,
            duration: 3000,
            backgroundColor: bgColors[type] || bgColors.info,
            className: type,
            position: "right",
            gravity: "top",
            close: true,
          }).showToast();
        } else {
          console.log(`${type.toUpperCase()}: ${message}`);
        }
      } catch (error) {
        console.error("Notification error:", error);
      }
    },
  },
};
</script>

<style scoped>
.surname {
  text-transform: capitalize !important;
}

.modern-dashboard {
  min-height: 100vh;
  position: relative;
  background: #f8fafc;
}

.modern-dashboard.dark-theme {
  background: linear-gradient(135deg, #202124 0%, #202124 100%);
  color: #e5e7eb;
}

.bg-gradient {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  opacity: 0.05;
  z-index: -1;
}

.glass-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  overflow: hidden;
}

.glass-header.dark-header {
  background: rgba(34, 34, 34, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.glass-header::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
  animation: shimmer 3s infinite;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-wrapper {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
}

.main-title {
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea, #764ba2);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.subtitle {
  color: #64748b;
  font-size: 1.1rem;
  margin: 4px 0 0 0;
}

.stats-cards {
  display: flex;
  gap: 16px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 16px 24px;
  border-radius: 16px;
  text-align: center;
  min-width: 80px;
}

.stat-number {
  font-size: 1.8rem;
  font-weight: 700;
}

.stat-label {
  font-size: 0.85rem;
  opacity: 0.9;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.modern-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  padding: 14px 28px;
  border-radius: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
}

.modern-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 40px rgba(102, 126, 234, 0.4);
}

.modern-btn.secondary {
  background: linear-gradient(135deg, #11998e, #38ef7d);
  box-shadow: 0 10px 30px rgba(17, 153, 142, 0.3);
}

.filter-panel {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 24px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
}

.search-wrapper {
  margin-bottom: 20px;
}

.search-box {
  position: relative;
  max-width: 500px;
  margin: 0 auto;
}

.search-input {
  width: 100%;
  padding: 16px 20px 16px 50px;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  font-size: 1.1rem;
  transition: all 0.3s ease;
  background: white;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}

.filter-chips {
  display: flex;
  gap: 24px;
  justify-content: center;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-weight: 600;
  color: #475569;
  font-size: 0.9rem;
}

.modern-select {
  padding: 12px 16px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  background: white;
  font-size: 1rem;
  min-width: 160px;
  transition: all 0.3s ease;
}

.modern-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 24px;
}

.student-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.student-avatar {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 700;
  font-size: 1rem;
}

.student-info {
  flex: 1;
}

.student-name {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 4px 0;
}

.student-subject {
  color: #667eea;
  font-weight: 600;
  margin: 0;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn.edit {
  background: #f0f9ff;
  color: #0ea5e9;
}

.action-btn.delete {
  background: #fef2f2;
  color: #ef4444;
}

.action-btn:hover {
  transform: scale(1.1);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #64748b;
}

.info-icon {
  color: #94a3b8;
}

.payment-amount {
  color: #059669;
  font-weight: 600;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.loading-text {
  margin-top: 20px;
  color: #64748b;
  font-size: 1.1rem;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 40px;
}

.page-btn {
  width: 44px;
  height: 44px;
  border: none;
  background: white;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

.page-btn:hover:not(:disabled) {
  background: #667eea;
  color: white;
  transform: translateY(-2px);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  padding: 12px 24px;
  background: white;
  border-radius: 12px;
  font-weight: 600;
  color: #475569;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 20px;
  }

  .action-buttons {
    width: 100%;
    justify-content: center;
  }

  .main-title {
    font-size: 2rem;
  }

  .data-grid {
    grid-template-columns: 1fr;
  }

  .filter-chips {
    flex-direction: column;
    align-items: center;
  }

  .search-input {
    font-size: 1rem;
  }
}
</style>
