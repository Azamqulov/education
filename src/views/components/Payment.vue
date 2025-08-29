<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <v-card class="table-card rounded-lg overflow-hidden elevation-3 mt-10">
          <v-card-title class="primary white--text py-3">
            <v-icon large color="blue" class="mr-2">mdi-cash-register</v-icon>
            <span class="text-h5 font-weight-bold">O'quvchilar To'lov Jadvali</span>
            <v-spacer></v-spacer>

            <!-- Yil tanlash -->
            <v-row class="d-flex align-center justify-end mt-10">
              <v-col cols="6">
                <v-select v-model="selectedYear" :items="availableYears" label="Yilni tanlang" dense filled dark clearable
                  class="mr-3 h-25"  @change="onYearChange"></v-select>

              </v-col cols="6">
              <v-text-field  v-model="search"   label="Qidirish"
                 dense filled dark clearable class="search-field  h-25"></v-text-field>
            </v-row>
          </v-card-title>

          <!-- Real-time statistika -->
          <v-card-subtitle class="pa-0">
            <v-row class="ma-0 stat-summary py-2 px-3">
              <v-col cols="12" md="3" sm="6" class="py-1">
                <v-chip color="primary" outlined label class="px-2 stat-chip">
                  <v-icon left small>mdi-account-group</v-icon>
                  <span>Jami o'quvchilar: <b>{{ filteredStudents.length }}</b></span>
                </v-chip>
              </v-col>
              <v-col cols="12" md="3" sm="6" class="py-1">
                <v-chip color="success" outlined label class="px-2 stat-chip">
                  <v-icon left small>mdi-check-circle</v-icon>
                  <span>To'langan: <b>{{ calculateTotalPaid() }}</b></span>
                </v-chip>
              </v-col>
              <v-col cols="12" md="3" sm="6" class="py-1">
                <v-chip color="error" outlined label class="px-2 stat-chip">
                  <v-icon left small>mdi-close-circle</v-icon>
                  <span>To'lanmagan: <b>{{ totalMonthsInYear - calculateTotalPaid() }}</b></span>
                </v-chip>
              </v-col>
              <v-col cols="12" md="3" sm="6" class="py-1">
                <v-chip :color="getTotalColor(calculateTotalPaid(), totalMonthsInYear)" outlined label
                  class="px-2 stat-chip">
                  <v-icon left small>mdi-percent</v-icon>
                  <span>Umumiy: <b>{{ calculateTotalPercentage() }}%</b></span>
                </v-chip>
              </v-col>
            </v-row>
          </v-card-subtitle>

          <!-- Jadval asosiy qismi -->
          <v-data-table :headers="dynamicHeaders" :items="filteredStudents" :items-per-page="10" :search="search"
            :footer-props="{
              'items-per-page-options': [5, 10, 15, 20, -1],
              'items-per-page-text': 'Bir sahifada:',
              'show-first-last-page': true
            }" item-key="id" class="elevation-0" dense :loading="loading" loading-text="Ma'lumotlar yuklanmoqda..."
            no-data-text="Ma'lumotlar topilmadi">
            <!-- O'quvchilar qatori -->
            <template v-slot:item="{ item, index }">
              <tr :class="{ 'payment-row': true, 'even-row': index % 2 === 0 }">
                <td class="text-center font-weight-medium">{{ index + 1 }}</td>
                <td>
                  <div class="d-flex align-center">
                    <v-avatar :color="getRandomColor(item.id)" size="32" class="mr-2">
                      <span class="white--text">{{ getInitials(item) }}</span>
                    </v-avatar>
                    <div>
                      <div class="font-weight-medium text-capitalize">{{ item.surname }} {{ item.name }}</div>
                      <div class="text-caption" v-if="item.teacher && item.teacher.name">
                        <v-icon small class="mr-1">mdi-account-tie</v-icon>
                        {{ item.teacher.name }}
                      </div>
                    </div>
                  </div>
                </td>

                <!-- To'lov checkboxlar -->
                <td v-for="(month, monthIndex) in currentYearMonths" :key="monthIndex"
                  class="text-center payment-cell px-0">
                  <v-tooltip bottom>
                    <template v-slot:activator="{ on, attrs }">
                      <v-btn icon small @click="togglePayment(item.id, month.year, month.month)" :class="{
                        'payment-icon-btn': true,
                        'paid': isMonthPaid(item, month.year, month.month),
                        'unpaid': !isMonthPaid(item, month.year, month.month),
                        'current-month': isCurrentMonth(month.year, month.month)
                      }" :disabled="loading" v-bind="attrs" v-on="on">
                        <v-icon small>
                          {{ isMonthPaid(item, month.year, month.month) ? 'mdi-check-circle' :
                          'mdi-close-circle-outline' }}
                        </v-icon>
                      </v-btn>
                    </template>
                    <span>{{ month.fullName }} {{ month.year }}</span>
                  </v-tooltip>
                  <div class="month-label">{{ month.shortName }}</div>
                </td>

                <!-- Status uchun qo'shimcha ustun -->
                <td class="text-center">
                  <v-chip x-small :color="getStatusColor(item)" text-color="white" label>
                    {{ getPaymentStatus(item) }}
                  </v-chip>
                </td>
              </tr>
            </template>

            <!-- Oylik statistika -->
            <template v-slot:body.append>
              <tr class="total-row font-weight-bold">
                <td colspan="2" class="text-subtitle-1 py-2">
                  <v-icon small class="mr-2">mdi-chart-bar</v-icon>
                  Oylik Statistika
                </td>
                <td v-for="(month, monthIndex) in currentYearMonths" :key="monthIndex" class="text-center">
                  <v-badge :content="calculateMonthlyTotal(month.year, month.month)"
                    :color="getTotalColor(calculateMonthlyTotal(month.year, month.month), filteredStudents.length)"
                    inline class="monthly-badge"></v-badge>
                  <div class="percentage-text">
                    {{ calculateMonthlyPercentage(month.year, month.month) }}%
                  </div>
                </td>
                <td class="text-center">
                  <v-chip small :color="getTotalColor(calculateTotalPaid(), totalMonthsInYear)" text-color="white">
                    {{ calculateTotalPercentage() }}%
                  </v-chip>
                </td>
              </tr>
            </template>
          </v-data-table>

          <!-- Statistika grafigi -->
          <v-divider></v-divider>
          <v-card-actions class="pa-4 stats-panel">
            <v-row>
              <v-col cols="12" md="12">
                <v-row>
                  <v-col cols="12" sm="4">
                    <v-card outlined class="stat-card">
                      <div class="stat-divider primary"></div>
                      <v-card-text class="text-center">
                        <div class="text-overline">O'quvchilar</div>
                        <div class="text-h4 font-weight-bold primary--text">{{ filteredStudents.length }}</div>
                        <div class="text-caption mt-1">Jami o'quvchilar soni</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="12" sm="4">
                    <v-card outlined class="stat-card">
                      <div class="stat-divider success"></div>
                      <v-card-text class="text-center">
                        <div class="text-overline">To'langan</div>
                        <div class="text-h4 font-weight-bold success--text">{{ calculateTotalPaid() }}</div>
                        <div class="text-caption mt-1">{{ selectedYear }} yilida to'langan</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                  <v-col cols="12" sm="4">
                    <v-card outlined class="stat-card">
                      <div class="stat-divider error"></div>
                      <v-card-text class="text-center">
                        <div class="text-overline">To'lanmagan</div>
                        <div class="text-h4 font-weight-bold error--text">
                          {{ totalMonthsInYear - calculateTotalPaid() }}
                        </div>
                        <div class="text-caption mt-1">{{ selectedYear }} yilida to'lanmagan</div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
                <v-row class="mt-2">
                  <v-col cols="12">
                    <v-alert dense text color="info" border="left" class="mb-0">
                      <div class="d-flex align-center">
                        <v-icon color="info" class="mr-2">mdi-information</v-icon>
                        <span>
                          <strong>{{ selectedYear }}</strong> yilida eng yuqori to'lov oyida:
                          <strong>{{ getBestMonth() }}</strong> -
                          <strong>{{ getBestMonthPercentage() }}%</strong> to'langan.
                        </span>
                      </div>
                    </v-alert>
                  </v-col>
                </v-row>
              </v-col>
            </v-row>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script>
import { db } from "@/firebaseConfig";
import {
  collection,
  getDocs,
  doc,
  updateDoc,
  query,
  where,
  onSnapshot
} from "firebase/firestore";
import Toastify from "toastify-js";

export default {
  name: "StudentPaymentsTable",
  data() {
    return {
      search: "",
      loading: true,
      unsubscribe: null,
      selectedYear: new Date().getFullYear(),
      months: [
        { name: "Yanvar", short: "Yan" },
        { name: "Fevral", short: "Fev" },
        { name: "Mart", short: "Mar" },
        { name: "Aprel", short: "Apr" },
        { name: "May", short: "May" },
        { name: "Iyun", short: "Iyn" },
        { name: "Iyul", short: "Iyl" },
        { name: "Avgust", short: "Avg" },
        { name: "Sentabr", short: "Sen" },
        { name: "Oktabr", short: "Okt" },
        { name: "Noyabr", short: "Noy" },
        { name: "Dekabr", short: "Dek" },
      ],
      currentUser: null,
      role: null,
      students: [],
      colors: ["#1976D2", "#9C27B0", "#E91E63", "#F44336", "#4CAF50", "#FF9800", "#795548", "#607D8B"],
    };
  },
  computed: {
    // Mavjud yillar ro'yxati
    availableYears() {
      const currentYear = new Date().getFullYear();
      const years = [];
      for (let i = currentYear - 0; i <= currentYear + 1; i++) {
        years.push(i);
      }
      return years;
    },

    // Joriy yil oylari
    currentYearMonths() {
      const currentDate = new Date();
      const currentYear = currentDate.getFullYear();
      const currentMonth = currentDate.getMonth();

      return this.months.map((month, index) => {
        const monthYear = this.selectedYear;
        const isPastOrCurrent = this.selectedYear < currentYear ||
          (this.selectedYear === currentYear && index <= currentMonth);

        return {
          month: index,
          year: monthYear,
          fullName: month.name,
          shortName: month.short,
          isPastOrCurrent
        };
      });
    },

    // Dinamik header
    dynamicHeaders() {
      const baseHeaders = [
        { text: "№", align: "center", sortable: false, width: "50px" },
        { text: "F.I.SH", align: "start", sortable: true, value: "fullName", width: "220px" },
      ];

      const monthHeaders = this.currentYearMonths.map((month, index) => ({
        text: month.shortName,
        align: "center",
        sortable: false,
        value: `payments.${month.year}.${month.month}`,
        width: "60px"
      }));

      const statusHeader = [
        { text: "Status", align: "center", sortable: true, value: "status", width: "90px" },
      ];

      return [...baseHeaders, ...monthHeaders, ...statusHeader];
    },

    filteredStudents() {
      if (!this.students.length) return [];

      let filtered = [...this.students];

      if (this.role && this.role !== "admin") {
        filtered = filtered.filter((student) =>
          student.teacher && student.teacher.name
            ? student.teacher.name.toLowerCase() === this.currentUser.toLowerCase()
            : false
        );
      }

      return filtered;
    },

    totalMonthsInYear() {
      return this.filteredStudents.length * this.currentYearMonths.length;
    }
  },
  methods: {
    // Yil o'zgarganda
    onYearChange() {
      this.showNotification(`${this.selectedYear} yili tanlandi`, "info");
    },

    // Real-time listener
    setupRealtimeListener() {
      this.loading = true;
      try {
        let studentQuery;
        if (this.role === "admin") {
          studentQuery = collection(db, "students");
        } else {
          studentQuery = query(
            collection(db, "students"),
            where("teacher.name", "==", this.currentUser)
          );
        }

        this.unsubscribe = onSnapshot(studentQuery, (snapshot) => {
          this.students = snapshot.docs.map((doc) => {
            const studentData = doc.data();

            return {
              ...studentData,
              id: doc.id,
              fullName: `${studentData.surname || ''} ${studentData.name || ''}`.trim(),
              payments: studentData.payments || {}
            };
          });
          this.loading = false;
        }, (error) => {
          console.error("Error in real-time listener:", error);
          this.showNotification("Real-time ma'lumotlarni olishda xatolik yuz berdi.", "error");
          this.loading = false;
        });
      } catch (error) {
        console.error("Error setting up listener:", error);
        this.showNotification("Ma'lumotlarni olishda xatolik yuz berdi.", "error");
        this.loading = false;
      }
    },

    // Oy to'langan yoki to'lanmaganligini tekshirish
    isMonthPaid(student, year, month) {
      if (!student.payments || !student.payments[year]) {
        return false;
      }
      return Boolean(student.payments[year][month]);
    },

    // Joriy oyni tekshirish
    isCurrentMonth(year, month) {
      const currentDate = new Date();
      return year === currentDate.getFullYear() && month === currentDate.getMonth();
    },

    // Oylik jami hisoblash
    calculateMonthlyTotal(year, month) {
      return this.filteredStudents.reduce((sum, student) => {
        return sum + (this.isMonthPaid(student, year, month) ? 1 : 0);
      }, 0);
    },

    // Oylik foiz hisoblash
    calculateMonthlyPercentage(year, month) {
      const total = this.filteredStudents.length;
      if (total === 0) return 0;
      return Math.round((this.calculateMonthlyTotal(year, month) / total) * 100);
    },

    // Jami to'langan hisoblash
    calculateTotalPaid() {
      return this.filteredStudents.reduce((total, student) => {
        let studentTotal = 0;
        this.currentYearMonths.forEach(month => {
          if (this.isMonthPaid(student, month.year, month.month)) {
            studentTotal++;
          }
        });
        return total + studentTotal;
      }, 0);
    },

    // Jami foiz hisoblash
    calculateTotalPercentage() {
      if (this.totalMonthsInYear === 0) return 0;
      return Math.round((this.calculateTotalPaid() / this.totalMonthsInYear) * 100);
    },

    // Eng yaxshi oyni topish
    getBestMonth() {
      if (!this.filteredStudents.length) return this.months[0].name;

      let maxPaid = -1;
      let bestMonth = this.months[0].name;

      this.currentYearMonths.forEach(month => {
        const paid = this.calculateMonthlyTotal(month.year, month.month);
        if (paid > maxPaid) {
          maxPaid = paid;
          bestMonth = month.fullName;
        }
      });

      return bestMonth;
    },

    // Eng yaxshi oy foizini hisoblash
    getBestMonthPercentage() {
      if (!this.filteredStudents.length) return 0;

      let maxPercentage = 0;

      this.currentYearMonths.forEach(month => {
        const percentage = this.calculateMonthlyPercentage(month.year, month.month);
        if (percentage > maxPercentage) {
          maxPercentage = percentage;
        }
      });

      return maxPercentage;
    },

    // To'lovni o'zgartirish
    async togglePayment(studentId, year, month) {
      if (this.loading) return;

      this.loading = true;
      const student = this.students.find(s => s.id === studentId);
      if (!student) {
        this.loading = false;
        return;
      }

      // Payments obyektini yangilash
      const updatedPayments = { ...student.payments };
      if (!updatedPayments[year]) {
        updatedPayments[year] = {};
      }

      updatedPayments[year][month] = !updatedPayments[year][month];

      const studentDoc = doc(db, "students", studentId);
      try {
        await updateDoc(studentDoc, { payments: updatedPayments });

        const monthName = this.months[month].name;
        this.showNotification(
          updatedPayments[year][month]
            ? `${monthName} ${year} to'lovi tasdiqlandi!`
            : `${monthName} ${year} to'lovi bekor qilindi!`,
          updatedPayments[year][month] ? "success" : "warning"
        );
      } catch (error) {
        console.error("Error updating payments:", error);
        this.showNotification("To'lovlarni yangilashda xatolik yuz berdi.", "error");
      } finally {
        this.loading = false;
      }
    },

    // Xabar ko'rsatish
    showNotification(message, type = "info") {
      const bgColors = {
        success: "linear-gradient(to right, #00b09b, #96c93d)",
        error: "linear-gradient(to right, #ff5f6d, #ffc3a0)",
        warning: "linear-gradient(to right, #f9d423, #ff4e50)",
        info: "linear-gradient(to right, #2193b0, #6dd5ed)"
      };

      Toastify({
        text: message,
        duration: 3000,
        close: true,
        gravity: "top",
        position: "right",
        backgroundColor: bgColors[type] || bgColors.info,
      }).showToast();
    },

    // Yardamchi funksiyalar
    getInitials(student) {
      const nameInitial = student.name ? student.name.charAt(0) : '';
      const surnameInitial = student.surname ? student.surname.charAt(0) : '';
      return (nameInitial + surnameInitial).toUpperCase();
    },

    getRandomColor(id) {
      if (!id) return this.colors[0];
      const colorIndex = id.charAt(0).charCodeAt(0) % this.colors.length;
      return this.colors[colorIndex];
    },

    // Status hisoblash
    getPaymentStatus(student) {
      const totalMonths = this.currentYearMonths.length;
      let paidCount = 0;

      this.currentYearMonths.forEach(month => {
        if (this.isMonthPaid(student, month.year, month.month)) {
          paidCount++;
        }
      });

      const percentage = totalMonths > 0 ? (paidCount / totalMonths) * 100 : 0;

      if (percentage === 100) return "To'liq";
      if (percentage >= 75) return "Yaxshi";
      if (percentage >= 50) return "O'rta";
      if (percentage > 0) return "Past";
      return "To'lanmagan";
    },

    // Status rangi
    getStatusColor(student) {
      const totalMonths = this.currentYearMonths.length;
      let paidCount = 0;

      this.currentYearMonths.forEach(month => {
        if (this.isMonthPaid(student, month.year, month.month)) {
          paidCount++;
        }
      });

      const percentage = totalMonths > 0 ? (paidCount / totalMonths) * 100 : 0;

      if (percentage === 100) return "success";
      if (percentage >= 75) return "light-green darken-1";
      if (percentage >= 50) return "amber darken-2";
      if (percentage > 0) return "deep-orange";
      return "error";
    },

    // Jami rang
    getTotalColor(paid, total) {
      if (!total || total === 0) return "grey";

      const percentage = (paid / total) * 100;

      if (percentage >= 90) return "success";
      if (percentage >= 70) return "light-green darken-1";
      if (percentage >= 50) return "amber darken-2";
      if (percentage > 30) return "deep-orange";
      return "error";
    }
  },
  created() {
    this.currentUser = localStorage.getItem("teacherName") || "";
    this.role = localStorage.getItem("userRole") || "";

    if (this.currentUser || this.role === "admin") {
      this.setupRealtimeListener();
    } else {
      console.error("No teacher logged in. Please log in to view students.");
      this.showNotification("Iltimos, tizimga kirgan o'qituvchi nomini tekshiring.", "error");
      this.loading = false;
    }
  },
  beforeDestroy() {
    if (this.unsubscribe) {
      this.unsubscribe();
    }
  }
};
</script>

<style>
.table-card {
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
}



.payment-row:hover {
  background-color: rgba(0, 0, 0, 0.03);
}

.even-row {
  background-color: rgba(0, 0, 0, 0.01);
}

.payment-icon-btn {
  width: 28px !important;
  height: 28px !important;
  margin: 0 auto;
  transition: all 0.2s ease;
}

.paid {
  color: #4CAF50 !important;
}

.unpaid {
  color: #bdbdbd !important;
}

.current-month {
  background-color: rgba(33, 150, 243, 0.1) !important;
  border: 1px solid #2196F3 !important;
}

.month-label {
  font-size: 10px;
  margin-top: 2px;
  color: #757575;
}

.stat-card {
  transition: transform 0.2s;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
}

.payment-cell {
  padding: 0 2px !important;
}

.stat-chip {
  font-size: 12px;
  height: 28px;
  width: 100%;
  justify-content: flex-start;
}

.monthly-badge {
  font-weight: bold;
}

.percentage-text {
  font-size: 10px;
  color: #757575;
  margin-top: 2px;
}

.stat-divider {
  height: 4px;
  width: 100%;
}

/* Responsive dizayn */
@media (max-width: 960px) {
  .search-field {
    max-width: 150px;
  }
}

@media (max-width: 600px) {
  .v-data-table {
    overflow-x: auto;
  }

  .stats-panel {
    padding: 8px !important;
  }

  .payment-cell {
    min-width: 50px;
  }

  .stat-chip {
    font-size: 10px;
  }

  .search-field {
    max-width: 120px;
  }
}
</style>