// All African countries with flag emoji and international dialing code.
// Used by the phone-number country-code picker on the Login screen.
// Uganda is placed first so it is the default selection (Ozzy's first market).

export interface Country {
  name: string;
  code: string; // ISO alpha-2 (used as a stable key)
  dial: string; // international dialing code, e.g. "+256"
  flag: string; // emoji flag
}

export const AFRICA_COUNTRIES: Country[] = [
  { name: 'Uganda', code: 'UG', dial: '+256', flag: '🇺🇬' },
  { name: 'Kenya', code: 'KE', dial: '+254', flag: '🇰🇪' },
  { name: 'Tanzania', code: 'TZ', dial: '+255', flag: '🇹🇿' },
  { name: 'Rwanda', code: 'RW', dial: '+250', flag: '🇷🇼' },
  { name: 'Burundi', code: 'BI', dial: '+257', flag: '🇧🇮' },
  { name: 'South Sudan', code: 'SS', dial: '+211', flag: '🇸🇸' },
  { name: 'Ethiopia', code: 'ET', dial: '+251', flag: '🇪🇹' },
  { name: 'Somalia', code: 'SO', dial: '+252', flag: '🇸🇴' },
  { name: 'Djibouti', code: 'DJ', dial: '+253', flag: '🇩🇯' },
  { name: 'Eritrea', code: 'ER', dial: '+291', flag: '🇪🇷' },
  { name: 'Nigeria', code: 'NG', dial: '+234', flag: '🇳🇬' },
  { name: 'Ghana', code: 'GH', dial: '+233', flag: '🇬🇭' },
  { name: 'Senegal', code: 'SN', dial: '+221', flag: '🇸🇳' },
  { name: "Côte d'Ivoire", code: 'CI', dial: '+225', flag: '🇨🇮' },
  { name: 'Mali', code: 'ML', dial: '+223', flag: '🇲🇱' },
  { name: 'Burkina Faso', code: 'BF', dial: '+226', flag: '🇧🇫' },
  { name: 'Niger', code: 'NE', dial: '+227', flag: '🇳🇪' },
  { name: 'Benin', code: 'BJ', dial: '+229', flag: '🇧🇯' },
  { name: 'Togo', code: 'TG', dial: '+228', flag: '🇹🇬' },
  { name: 'Guinea', code: 'GN', dial: '+224', flag: '🇬🇳' },
  { name: 'Guinea-Bissau', code: 'GW', dial: '+245', flag: '🇬🇼' },
  { name: 'Sierra Leone', code: 'SL', dial: '+232', flag: '🇸🇱' },
  { name: 'Liberia', code: 'LR', dial: '+231', flag: '🇱🇷' },
  { name: 'The Gambia', code: 'GM', dial: '+220', flag: '🇬🇲' },
  { name: 'Mauritania', code: 'MR', dial: '+222', flag: '🇲🇷' },
  { name: 'Cape Verde', code: 'CV', dial: '+238', flag: '🇨🇻' },
  { name: 'Cameroon', code: 'CM', dial: '+237', flag: '🇨🇲' },
  { name: 'Chad', code: 'TD', dial: '+235', flag: '🇹🇩' },
  { name: 'Central African Republic', code: 'CF', dial: '+236', flag: '🇨🇫' },
  { name: 'Gabon', code: 'GA', dial: '+241', flag: '🇬🇦' },
  { name: 'Congo (Brazzaville)', code: 'CG', dial: '+242', flag: '🇨🇬' },
  { name: 'Congo (DRC)', code: 'CD', dial: '+243', flag: '🇨🇩' },
  { name: 'Equatorial Guinea', code: 'GQ', dial: '+240', flag: '🇬🇶' },
  { name: 'São Tomé and Príncipe', code: 'ST', dial: '+239', flag: '🇸🇹' },
  { name: 'Angola', code: 'AO', dial: '+244', flag: '🇦🇴' },
  { name: 'Zambia', code: 'ZM', dial: '+260', flag: '🇿🇲' },
  { name: 'Zimbabwe', code: 'ZW', dial: '+263', flag: '🇿🇼' },
  { name: 'Malawi', code: 'MW', dial: '+265', flag: '🇲🇼' },
  { name: 'Mozambique', code: 'MZ', dial: '+258', flag: '🇲🇿' },
  { name: 'Botswana', code: 'BW', dial: '+267', flag: '🇧🇼' },
  { name: 'Namibia', code: 'NA', dial: '+264', flag: '🇳🇦' },
  { name: 'South Africa', code: 'ZA', dial: '+27', flag: '🇿🇦' },
  { name: 'Lesotho', code: 'LS', dial: '+266', flag: '🇱🇸' },
  { name: 'Eswatini', code: 'SZ', dial: '+268', flag: '🇸🇿' },
  { name: 'Madagascar', code: 'MG', dial: '+261', flag: '🇲🇬' },
  { name: 'Mauritius', code: 'MU', dial: '+230', flag: '🇲🇺' },
  { name: 'Seychelles', code: 'SC', dial: '+248', flag: '🇸🇨' },
  { name: 'Comoros', code: 'KM', dial: '+269', flag: '🇰🇲' },
  { name: 'Egypt', code: 'EG', dial: '+20', flag: '🇪🇬' },
  { name: 'Libya', code: 'LY', dial: '+218', flag: '🇱🇾' },
  { name: 'Tunisia', code: 'TN', dial: '+216', flag: '🇹🇳' },
  { name: 'Algeria', code: 'DZ', dial: '+213', flag: '🇩🇿' },
  { name: 'Morocco', code: 'MA', dial: '+212', flag: '🇲🇦' },
  { name: 'Sudan', code: 'SD', dial: '+249', flag: '🇸🇩' },
];
