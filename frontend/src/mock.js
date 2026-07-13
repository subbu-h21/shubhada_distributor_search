// Mock data for PharmaScrape clone

export const PORTALS = [
  { id: 'sunshop', name: 'SUNSHOP', baseUrl: 'https://www.sunshop.co.in', status: 'ACTIVE', description: 'Sunshop portal for multiple distributors' },
  { id: 'chethana', name: 'CHETHANA', baseUrl: 'http://www.chiragpharma.in', status: 'ACTIVE', description: 'Chethana distribution portal' },
  { id: 'vardhaman', name: 'VARDHAMAN', baseUrl: 'http://easysol.co.in', status: 'ACTIVE', description: 'Vardhaman medisales web order portal' },
  { id: 'medplus', name: 'MEDPLUS', baseUrl: 'https://medplus.in', status: 'INACTIVE', description: 'MedPlus wholesale portal' },
  { id: 'apollo', name: 'APOLLO', baseUrl: 'https://apollo.co.in', status: 'ACTIVE', description: 'Apollo pharmacy distributor portal' },
];

export const DEFAULT_TARGETS = [
  {
    id: 't1',
    name: 'SAROJ PHARMA',
    url: 'https://www.sunshop.co.in/sunfilter/saroj',
    portal: 'SUNSHOP',
    selected: true,
  },
  {
    id: 't2',
    name: 'HEGDE BROTHER',
    url: 'https://www.sunshop.co.in/sunfilter/hegde',
    portal: 'SUNSHOP',
    selected: true,
  },
  {
    id: 't3',
    name: 'KAPILA PHARMA',
    url: 'https://www.sunshop.co.in/sunfilter/kapila',
    portal: 'SUNSHOP',
    selected: true,
  },
  {
    id: 't4',
    name: 'KAPILA MEDICAL AGENCIES',
    url: 'https://www.sunshop.co.in/sunfilter/kapila-med',
    portal: 'SUNSHOP',
    selected: true,
  },
  {
    id: 't5',
    name: 'CHIRAG PHARMA',
    url: 'http://www.chiragpharma.in/',
    portal: 'CHETHANA',
    selected: true,
  },
  {
    id: 't6',
    name: 'VARDHAMAN MEDISALES PVT LTD',
    url: 'http://easysol.co.in/WebOrderRegistration',
    portal: 'VARDHAMAN',
    selected: true,
  },
  {
    id: 't7',
    name: 'SRI SAI MEDICALS',
    url: 'https://www.sunshop.co.in/sunfilter/srisai',
    portal: 'SUNSHOP',
    selected: false,
  },
  {
    id: 't8',
    name: 'BHARAT MEDICOS',
    url: 'http://easysol.co.in/WebOrderRegistration/bharat',
    portal: 'VARDHAMAN',
    selected: false,
  },
];

export const HISTORY = [
  {
    id: 'h1',
    product: 'PROLOMET XL 25',
    timestamp: '2025-07-12T14:32:00Z',
    duration: '4.2s',
    targetsRun: 6,
    found: 4,
    outOfStock: 2,
    status: 'COMPLETED',
  },
  {
    id: 'h2',
    product: 'PANTOP DSR',
    timestamp: '2025-07-12T11:08:00Z',
    duration: '3.8s',
    targetsRun: 8,
    found: 6,
    outOfStock: 2,
    status: 'COMPLETED',
  },
  {
    id: 'h3',
    product: 'DOLO 650',
    timestamp: '2025-07-11T18:45:00Z',
    duration: '5.1s',
    targetsRun: 5,
    found: 5,
    outOfStock: 0,
    status: 'COMPLETED',
  },
  {
    id: 'h4',
    product: 'AZITHRAL 500',
    timestamp: '2025-07-11T09:20:00Z',
    duration: '2.9s',
    targetsRun: 4,
    found: 1,
    outOfStock: 3,
    status: 'COMPLETED',
  },
  {
    id: 'h5',
    product: 'MONTAIR LC',
    timestamp: '2025-07-10T16:15:00Z',
    duration: '6.7s',
    targetsRun: 8,
    found: 3,
    outOfStock: 4,
    status: 'PARTIAL',
  },
  {
    id: 'h6',
    product: 'CROCIN ADVANCE',
    timestamp: '2025-07-10T10:02:00Z',
    duration: '3.3s',
    targetsRun: 6,
    found: 4,
    outOfStock: 2,
    status: 'COMPLETED',
  },
];

// Generates deterministic extraction result based on target list
export function generateExtractionResults(product, targets) {
  const outcomes = ['IN_STOCK', 'OUT_OF_STOCK', 'IN_STOCK', 'IN_STOCK', 'OUT_OF_STOCK', 'ERROR'];
  return targets.map((t, i) => {
    const status = outcomes[i % outcomes.length];
    const price = status === 'IN_STOCK' ? (Math.random() * 100 + 20).toFixed(2) : null;
    const stock = status === 'IN_STOCK' ? Math.floor(Math.random() * 200 + 10) : 0;
    return {
      targetId: t.id,
      targetName: t.name,
      portal: t.portal,
      url: t.url,
      product,
      status,
      price,
      stock,
      mrp: status === 'IN_STOCK' ? (parseFloat(price) * 1.15).toFixed(2) : null,
      pack: status === 'IN_STOCK' ? '10x10' : null,
      responseMs: Math.floor(Math.random() * 900 + 200),
      lastUpdated: new Date().toISOString(),
    };
  });
}
