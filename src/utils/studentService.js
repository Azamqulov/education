import { db } from '@/firebaseConfig';
import { 
  collection, 
  addDoc, 
  updateDoc, 
  deleteDoc, 
  doc, 
  serverTimestamp 
} from 'firebase/firestore';

/**
 * O'quvchi qo'shish xizmati
 * @param {Object} studentData - O'quvchi ma'lumotlari
 * @returns {Promise<string>} - Yangi o'quvchi ID si
 */
export async function addStudent(studentData) {
  try {
    // Ma'lumotlarni tayyorlash
    const preparedData = {
      ...studentData,
      // Teacher obyektini to'g'ri formatda saqlash
      teacher: typeof studentData.teacher === 'string' 
        ? { name: studentData.teacher }
        : studentData.teacher,
      
      // Center maydonini majburiy qilish
      center: studentData.center || 'london-lc',
      
      // Qo'shimcha meta ma'lumotlar
      createdAt: serverTimestamp(),
      updatedAt: serverTimestamp(),
      
      // Telegram bildirishnoma holati
      telegramNotified: false,
      telegramNotificationAttempted: false,
      
      // To'lov tarixi (bo'sh massiv)
      payments: Array(12).fill(false),
      
      // Faol holat
      isActive: true
    };

    // Firestore ga qo'shish
    const docRef = await addDoc(collection(db, 'students'), preparedData);
    
    console.log('O\'quvchi muvaffaqiyatli qo\'shildi:', docRef.id);
    return docRef.id;
    
  } catch (error) {
    console.error('O\'quvchi qo\'shishda xatolik:', error);
    throw new Error(`O'quvchi qo'shishda xatolik: ${error.message}`);
  }
}

/**
 * O'quvchi ma'lumotlarini yangilash
 * @param {string} studentId - O'quvchi ID si
 * @param {Object} updateData - Yangilanayotgan ma'lumotlar
 * @returns {Promise<void>}
 */
export async function updateStudent(studentId, updateData) {
  try {
    const studentRef = doc(db, 'students', studentId);
    
    // Ma'lumotlarni tayyorlash
    const preparedData = {
      ...updateData,
      // Teacher obyektini to'g'ri formatda saqlash
      teacher: typeof updateData.teacher === 'string' 
        ? { name: updateData.teacher }
        : updateData.teacher,
      
      // Yangilanish vaqtini qo'shish
      updatedAt: serverTimestamp()
    };

    await updateDoc(studentRef, preparedData);
    
    console.log('O\'quvchi ma\'lumotlari muvaffaqiyatli yangilandi:', studentId);
    
  } catch (error) {
    console.error('O\'quvchi yangilashda xatolik:', error);
    throw new Error(`O'quvchi yangilashda xatolik: ${error.message}`);
  }
}

/**
 * O'quvchini o'chirish
 * @param {string} studentId - O'quvchi ID si
 * @returns {Promise<void>}
 */
export async function deleteStudent(studentId) {
  try {
    await deleteDoc(doc(db, 'students', studentId));
    
    console.log('O\'quvchi muvaffaqiyatli o\'chirildi:', studentId);
    
  } catch (error) {
    console.error('O\'quvchi o\'chirishda xatolik:', error);
    throw new Error(`O'quvchi o'chirishda xatolik: ${error.message}`);
  }
}

/**
 * Telegram bildirishnoma holatini yangilash
 * @param {string} studentId - O'quvchi ID si
 * @param {boolean} success - Muvaffaqiyat holati
 * @param {string} error - Xatolik xabari (ixtiyoriy)
 * @returns {Promise<void>}
 */
export async function updateTelegramNotificationStatus(studentId, success, error = null) {
  try {
    const studentRef = doc(db, 'students', studentId);
    
    const updateData = {
      telegramNotified: success,
      telegramNotificationAttempted: true,
      telegramNotificationAttemptedAt: serverTimestamp()
    };
    
    if (error) {
      updateData.telegramNotificationError = error;
    } else if (success) {
      updateData.telegramNotifiedAt = serverTimestamp();
    }

    await updateDoc(studentRef, updateData);
    
    console.log('Telegram bildirishnoma holati yangilandi:', studentId, success);
    
  } catch (updateError) {
    console.error('Telegram holati yangilashda xatolik:', updateError);
  }
}

/**
 * O'quvchi ma'lumotlarini validatsiya qilish
 * @param {Object} studentData - O'quvchi ma'lumotlari
 * @returns {Object} - Validatsiya natijasi
 */
export function validateStudentData(studentData) {
  const errors = [];
  const warnings = [];

  // Majburiy maydonlar
  const requiredFields = [
    { field: 'name', label: 'Ism' },
    { field: 'surname', label: 'Familya' },
    { field: 'phone', label: 'Telefon' },
    { field: 'subject', label: 'Fan' },
    { field: 'teacher', label: 'O\'qituvchi' },
    { field: 'center', label: 'Filial' }
  ];

  for (const { field, label } of requiredFields) {
    if (!studentData[field] || studentData[field].toString().trim() === '') {
      errors.push(`${label} majburiy maydon`);
    }
  }

  // Telefon raqami validatsiyasi
  if (studentData.phone) {
    const phoneRegex = /^[\+]?[0-9\s\-\(\)]{9,15}$/;
    if (!phoneRegex.test(studentData.phone)) {
      errors.push('Telefon raqami noto\'g\'ri formatda');
    }
  }

  // Ism va familya uzunligi
  if (studentData.name && studentData.name.length < 2) {
    errors.push('Ism kamida 2 ta harf bo\'lishi kerak');
  }

  if (studentData.surname && studentData.surname.length < 2) {
    errors.push('Familya kamida 2 ta harf bo\'lishi kerak');
  }

  // To'lov miqdori
  if (studentData.payment) {
    const payment = parseInt(studentData.payment);
    if (isNaN(payment) || payment < 0) {
      errors.push('To\'lov miqdori noto\'g\'ri');
    } else if (payment === 0) {
      warnings.push('To\'lov miqdori 0 ga teng');
    }
  }

  // Sana validatsiyasi
  if (studentData.date) {
    const date = new Date(studentData.date);
    const today = new Date();
    
    if (isNaN(date.getTime())) {
      errors.push('Sana noto\'g\'ri formatda');
    } else if (date > today) {
      warnings.push('Sana kelajakda ko\'rsatilgan');
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Telefon raqamini formatlash
 * @param {string} phone - Telefon raqami
 * @returns {string} - Formatlangan telefon raqami
 */
export function formatPhoneNumber(phone) {
  if (!phone) return '';
  
  // Faqat raqamlarni qoldirish
  const digits = phone.toString().replace(/\D/g, '');
  
  // Uzbek telefon raqami formatini tekshirish
  if (digits.length === 9) {
    return `+998 ${digits.substring(0, 2)} ${digits.substring(2, 5)}-${digits.substring(5, 7)}-${digits.substring(7)}`;
  } else if (digits.length === 12 && digits.startsWith('998')) {
    return `+${digits.substring(0, 3)} ${digits.substring(3, 5)} ${digits.substring(5, 8)}-${digits.substring(8, 10)}-${digits.substring(10)}`;
  }
  
  return phone;
}

/**
 * O'quvchi ma'lumotlarini eksport uchun tayyorlash
 * @param {Array} students - O'quvchilar ro'yxati
 * @returns {Array} - Eksport uchun tayyorlangan ma'lumotlar
 */
export function prepareStudentsForExport(students) {
  return students.map((student, index) => ({
    '№': index + 1,
    'Ism': student.name || '',
    'Familya': student.surname || '',
    'Fan': student.subject || '',
    'O\'qituvchi': student.teacher?.name || student.teacher || '',
    'Telefon': formatPhoneNumber(student.phone),
    'To\'lov': student.payment ? `${parseInt(student.payment).toLocaleString()} so'm` : '0 so\'m',
    'Sana': student.date ? new Date(student.date).toLocaleDateString('uz-UZ') : '',
    'Filial': student.center || '',
    'Telegram Bildirildi': student.telegramNotified ? 'Ha' : 'Yo\'q',
    'Yaratilgan': student.createdAt ? new Date(student.createdAt.toDate()).toLocaleDateString('uz-UZ') : ''
  }));
}