const functions = require('firebase-functions');
const admin = require('firebase-admin');
const axios = require('axios');

// Firebase Admin SDK ni ishga tushirish
if (!admin.apps.length) {
  admin.initializeApp();
}

const db = admin.firestore();

// Telegram Bot konfiguratsiyasi
const TELEGRAM_BOT_TOKEN = functions.config().telegram?.bot_token || process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = functions.config().telegram?.chat_id || process.env.TELEGRAM_CHAT_ID;
const CRM_BASE_URL = functions.config().crm?.base_url || process.env.CRM_BASE_URL || 'https://your-crm-domain.com';

// Telegram API URL
const TELEGRAM_API_URL = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}`;

/**
 * Matnni Markdown V2 formatiga escape qilish
 * @param {string} text - Escape qilinadigan matn
 * @returns {string} - Escape qilingan matn
 */
function escapeMarkdownV2(text) {
  if (!text) return '';
  return text.toString().replace(/[_*\[\]()~`>#+=|{}.!-]/g, '\\$&');
}

/**
 * Telefon raqamini formatlash
 * @param {string} phone - Telefon raqami
 * @returns {string} - Formatlangan telefon raqami
 */
function formatPhone(phone) {
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
 * Telegram xabarini yuborish (retry mexanizmi bilan)
 * @param {string} message - Yuborilayotgan xabar
 * @param {Object} inlineKeyboard - Inline klaviatura (ixtiyoriy)
 * @param {number} retryCount - Retry soni
 * @returns {Promise<boolean>} - Yuborish muvaffaqiyati
 */
async function sendTelegramMessage(message, inlineKeyboard = null, retryCount = 0) {
  const maxRetries = 3;
  const backoffDelays = [1000, 3000, 9000]; // 1s, 3s, 9s
  
  try {
    const payload = {
      chat_id: TELEGRAM_CHAT_ID,
      text: message,
      parse_mode: 'MarkdownV2',
      disable_web_page_preview: true
    };
    
    if (inlineKeyboard) {
      payload.reply_markup = {
        inline_keyboard: inlineKeyboard
      };
    }
    
    const response = await axios.post(`${TELEGRAM_API_URL}/sendMessage`, payload, {
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (response.data.ok) {
      console.log('Telegram xabari muvaffaqiyatli yuborildi:', response.data.result.message_id);
      return true;
    } else {
      throw new Error(`Telegram API xatosi: ${response.data.description}`);
    }
    
  } catch (error) {
    console.error(`Telegram xabarini yuborishda xatolik (${retryCount + 1}/${maxRetries}):`, error.message);
    
    // Retry mexanizmi
    if (retryCount < maxRetries - 1) {
      const delay = backoffDelays[retryCount];
      console.log(`${delay}ms kutib, qayta urinish...`);
      
      await new Promise(resolve => setTimeout(resolve, delay));
      return sendTelegramMessage(message, inlineKeyboard, retryCount + 1);
    }
    
    // Barcha retry urinishlari muvaffaqiyatsiz bo'lsa
    console.error('Barcha retry urinishlari muvaffaqiyatsiz tugadi');
    return false;
  }
}

/**
 * O'quvchi ma'lumotlarini validatsiya qilish
 * @param {Object} studentData - O'quvchi ma'lumotlari
 * @returns {boolean} - Validatsiya natijasi
 */
function validateStudentData(studentData) {
  const requiredFields = ['name', 'surname', 'subject', 'teacher', 'phone'];
  
  for (const field of requiredFields) {
    if (!studentData[field] || studentData[field].toString().trim() === '') {
      console.warn(`Majburiy maydon yo'q yoki bo'sh: ${field}`);
      return false;
    }
  }
  
  return true;
}

/**
 * Telegram xabar matnini yaratish
 * @param {Object} studentData - O'quvchi ma'lumotlari
 * @param {string} studentId - O'quvchi ID si
 * @returns {string} - Formatlangan xabar matni
 */
function createTelegramMessage(studentData, studentId) {
  // Ma'lumotlarni escape qilish
  const name = escapeMarkdownV2(`${studentData.name} ${studentData.surname}`);
  const subject = escapeMarkdownV2(studentData.subject);
  const teacher = escapeMarkdownV2(studentData.teacher?.name || studentData.teacher);
  const phone = escapeMarkdownV2(formatPhone(studentData.phone));
  const center = escapeMarkdownV2(studentData.center || 'london-lc');
  
  // Qo'shimcha ma'lumotlar
  const date = studentData.date ? escapeMarkdownV2(new Date(studentData.date).toLocaleDateString('uz-UZ')) : '';
  const payment = studentData.payment ? escapeMarkdownV2(`${parseInt(studentData.payment).toLocaleString()} so'm`) : '';
  
  let message = `*Yangi o'quvchi\\!* 📚\n\n`;
  message += `*Ism:* ${name}\n`;
  message += `*Fan:* ${subject}\n`;
  message += `*Ustoz:* ${teacher}\n`;
  message += `*Tel:* ${phone}\n`;
  message += `*Filial:* ${center}\n`;
  
  if (date) {
    message += `*Sana:* ${date}\n`;
  }
  
  if (payment) {
    message += `*To'lov:* ${payment}\n`;
  }
  
  message += `\n*ID:* \`${escapeMarkdownV2(studentId)}\``;
  
  return message;
}

/**
 * Inline klaviatura yaratish
 * @param {string} studentId - O'quvchi ID si
 * @returns {Array} - Inline klaviatura massivi
 */
function createInlineKeyboard(studentId) {
  const detailsUrl = `${CRM_BASE_URL}/students/${studentId}`;
  
  return [
    [
      {
        text: '📋 Batafsil',
        url: detailsUrl
      },
      {
        text: '✏️ Tahrirlash',
        url: `${CRM_BASE_URL}/students/${studentId}/edit`
      }
    ]
  ];
}

/**
 * Yangi o'quvchi qo'shilganda ishlaydigan Cloud Function
 */
exports.notifyNewStudent = functions.firestore
  .document('students/{studentId}')
  .onCreate(async (snap, context) => {
    try {
      const studentData = snap.data();
      const studentId = context.params.studentId;
      
      console.log('Yangi o\'quvchi qo\'shildi:', studentId, studentData);
      
      // Faqat London LC filiali uchun
      if (studentData.center !== 'london-lc') {
        console.log(`Bu o'quvchi London LC filialiga tegishli emas: ${studentData.center}`);
        return null;
      }
      
      // Telegram konfiguratsiyasini tekshirish
      if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
        console.error('Telegram konfiguratsiyasi to\'liq emas:', {
          botToken: !!TELEGRAM_BOT_TOKEN,
          chatId: !!TELEGRAM_CHAT_ID
        });
        return null;
      }
      
      // Ma'lumotlarni validatsiya qilish
      if (!validateStudentData(studentData)) {
        console.error('O\'quvchi ma\'lumotlari validatsiyadan o\'tmadi:', studentData);
        return null;
      }
      
      // Telegram xabarini yaratish
      const message = createTelegramMessage(studentData, studentId);
      const inlineKeyboard = createInlineKeyboard(studentId);
      
      console.log('Telegram xabari tayyorlandi:', message);
      
      // Telegram xabarini yuborish
      const success = await sendTelegramMessage(message, inlineKeyboard);
      
      if (success) {
        // Muvaffaqiyatli yuborilganini belgilash
        await snap.ref.update({
          telegramNotified: true,
          telegramNotifiedAt: admin.firestore.FieldValue.serverTimestamp()
        });
        
        console.log('Telegram bildirishnomasi muvaffaqiyatli yuborildi va belgilandi');
      } else {
        // Xatolikni belgilash
        await snap.ref.update({
          telegramNotified: false,
          telegramNotificationError: 'Failed to send after retries',
          telegramNotificationAttemptedAt: admin.firestore.FieldValue.serverTimestamp()
        });
        
        console.error('Telegram bildirishnomasi yuborilmadi');
      }
      
      return null;
      
    } catch (error) {
      console.error('notifyNewStudent funksiyasida xatolik:', error);
      
      // Xatolikni hujjatga yozish
      try {
        await snap.ref.update({
          telegramNotified: false,
          telegramNotificationError: error.message,
          telegramNotificationAttemptedAt: admin.firestore.FieldValue.serverTimestamp()
        });
      } catch (updateError) {
        console.error('Xatolik holatini yangilashda muammo:', updateError);
      }
      
      return null;
    }
  });

/**
 * O'quvchi ma'lumotlari yangilanganda ishlaydigan Cloud Function (ixtiyoriy)
 */
exports.notifyStudentUpdate = functions.firestore
  .document('students/{studentId}')
  .onUpdate(async (change, context) => {
    try {
      const beforeData = change.before.data();
      const afterData = change.after.data();
      const studentId = context.params.studentId;
      
      // Faqat London LC filiali uchun
      if (afterData.center !== 'london-lc') {
        return null;
      }
      
      // Muhim o'zgarishlarni tekshirish
      const importantFields = ['subject', 'teacher', 'payment', 'phone'];
      const changes = [];
      
      for (const field of importantFields) {
        if (beforeData[field] !== afterData[field]) {
          changes.push({
            field,
            before: beforeData[field],
            after: afterData[field]
          });
        }
      }
      
      // Agar muhim o'zgarishlar bo'lsa
      if (changes.length > 0 && TELEGRAM_BOT_TOKEN && TELEGRAM_CHAT_ID) {
        const studentName = escapeMarkdownV2(`${afterData.name} ${afterData.surname}`);
        
        let message = `*O'quvchi ma'lumotlari yangilandi\\!* ✏️\n\n`;
        message += `*O'quvchi:* ${studentName}\n`;
        message += `*ID:* \`${escapeMarkdownV2(studentId)}\`\n\n`;
        message += `*O'zgarishlar:*\n`;
        
        for (const change of changes) {
          const fieldName = {
            'subject': 'Fan',
            'teacher': 'Ustoz',
            'payment': 'To\'lov',
            'phone': 'Telefon'
          }[change.field] || change.field;
          
          const beforeValue = escapeMarkdownV2(change.before?.name || change.before || 'N/A');
          const afterValue = escapeMarkdownV2(change.after?.name || change.after || 'N/A');
          
          message += `• *${fieldName}:* ${beforeValue} → ${afterValue}\n`;
        }
        
        const inlineKeyboard = createInlineKeyboard(studentId);
        await sendTelegramMessage(message, inlineKeyboard);
        
        console.log('O\'quvchi yangilanish bildirishnomasi yuborildi:', studentId);
      }
      
      return null;
      
    } catch (error) {
      console.error('notifyStudentUpdate funksiyasida xatolik:', error);
      return null;
    }
  });

/**
 * Manual test funksiyasi (development uchun)
 */
exports.testTelegramNotification = functions.https.onRequest(async (req, res) => {
  try {
    if (req.method !== 'POST') {
      return res.status(405).json({ error: 'Faqat POST so\'rovlar qabul qilinadi' });
    }
    
    // Test ma'lumotlari
    const testStudentData = {
      name: 'Test',
      surname: 'Student',
      subject: 'Matematika',
      teacher: { name: 'Test Teacher' },
      phone: '+998901234567',
      center: 'london-lc',
      payment: '500000',
      date: new Date().toISOString()
    };
    
    const testStudentId = 'test_' + Date.now();
    
    // Xabar yaratish va yuborish
    const message = createTelegramMessage(testStudentData, testStudentId);
    const inlineKeyboard = createInlineKeyboard(testStudentId);
    
    const success = await sendTelegramMessage(message, inlineKeyboard);
    
    if (success) {
      res.json({ 
        success: true, 
        message: 'Test bildirishnomasi muvaffaqiyatli yuborildi',
        data: { testStudentData, message }
      });
    } else {
      res.status(500).json({ 
        success: false, 
        message: 'Test bildirishnomasi yuborilmadi' 
      });
    }
    
  } catch (error) {
    console.error('Test funksiyasida xatolik:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Test funksiyasida xatolik', 
      error: error.message 
    });
  }
});

/**
 * Telegram webhook uchun funksiya (ixtiyoriy)
 */
exports.telegramWebhook = functions.https.onRequest(async (req, res) => {
  try {
    if (req.method !== 'POST') {
      return res.status(200).send('OK');
    }
    
    const update = req.body;
    console.log('Telegram webhook update:', update);
    
    // Bu yerda Telegram dan kelgan xabarlarni qayta ishlash mumkin
    // Masalan, admin komandalarini qabul qilish
    
    res.status(200).send('OK');
    
  } catch (error) {
    console.error('Telegram webhook xatolik:', error);
    res.status(200).send('OK');
  }
});