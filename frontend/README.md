# 🌿 Emerald Flow - Sustainability Platform Frontend

A modern React frontend for the Sustainability Expert Platform, built to connect with the GoAI Platform backend.

## 🚀 Quick Start

### 1. Create React App with Vite

```bash
# From the goai-platform-v1 directory
cd frontend
npm create vite@latest . -- --template react-ts
npm install
```

### 2. Install Dependencies

```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install react-router-dom
npm install tailwindcss postcss autoprefixer
npm install lucide-react
npm install recharts
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-select
npm install clsx tailwind-merge
npm install date-fns
```

### 3. Setup Tailwind CSS

```bash
npx tailwindcss init -p
```

Update `tailwind.config.js`:
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        emerald: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
      },
    },
  },
  plugins: [],
}
```

### 4. Configure Environment

Create `.env`:
```env
VITE_API_URL=http://localhost:8000
```

### 5. Move API Files

```bash
mv api src/api
```

### 6. Setup React Query

In `src/main.tsx`:
```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <ReactQueryDevtools />
    </QueryClientProvider>
  </React.StrictMode>
);
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── api/                 # API layer (provided)
│   │   ├── config.ts        # API endpoints configuration
│   │   ├── types.ts         # TypeScript type definitions
│   │   ├── client.ts        # API client with all methods
│   │   ├── hooks.ts         # React Query hooks
│   │   └── index.ts         # Module exports
│   ├── components/
│   │   ├── ui/              # Reusable UI components
│   │   ├── dashboard/       # Dashboard components
│   │   ├── review/          # Review queue components
│   │   └── upload/          # Document upload components
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── ReviewQueue.tsx
│   │   ├── Upload.tsx
│   │   ├── Analytics.tsx
│   │   └── Settings.tsx
│   ├── hooks/               # Custom hooks
│   ├── contexts/            # React contexts (auth, theme)
│   ├── utils/               # Utility functions
│   ├── App.tsx
│   └── main.tsx
├── public/
├── .env
├── tailwind.config.js
└── package.json
```

## 🔌 API Connection

The API layer is pre-configured to connect to your backend:

### Using Hooks (Recommended)

```tsx
import { useReviewQueue, useReviewStats, useApproveItem } from '@/api';

function ReviewDashboard() {
  // Fetch queue with auto-refresh
  const { data: queue, isLoading } = useReviewQueue({ status: 'pending' });
  
  // Fetch stats
  const { data: stats } = useReviewStats();
  
  // Mutation for approving items
  const approveMutation = useApproveItem();
  
  const handleApprove = (id: string) => {
    approveMutation.mutate({ id });
  };
  
  if (isLoading) return <Spinner />;
  
  return (
    <div>
      <StatsCards stats={stats} />
      <QueueList items={queue?.items} onApprove={handleApprove} />
    </div>
  );
}
```

### Direct API Client

```tsx
import { apiClient } from '@/api';

// Fetch data directly
const stats = await apiClient.getReviewStats();

// Submit document
const result = await apiClient.submitDocument({
  text_content: 'PG&E Bill...',
  source: 'upload',
  company_id: 'xyz-corp-001'
});

// Smart process with auto-learn
const processed = await apiClient.smartProcessAuto({
  text_content: documentText,
  company_id: 'xyz-corp-001'
});
```

## 🎨 Component Examples

### Stats Card

```tsx
interface StatsCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  trend?: number;
  color?: 'emerald' | 'blue' | 'yellow' | 'red';
}

function StatsCard({ title, value, icon, trend, color = 'emerald' }: StatsCardProps) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700">
      <div className="flex items-center justify-between">
        <div className={`p-3 rounded-lg bg-${color}-500/20`}>
          {icon}
        </div>
        {trend && (
          <span className={trend > 0 ? 'text-emerald-500' : 'text-red-500'}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold text-white">{value}</p>
        <p className="text-slate-400 text-sm">{title}</p>
      </div>
    </div>
  );
}
```

### Queue Item Row

```tsx
function QueueItemRow({ item, onApprove, onReview }: QueueItemRowProps) {
  const confidenceColor = 
    item.confidence >= 0.9 ? 'bg-emerald-500' :
    item.confidence >= 0.7 ? 'bg-yellow-500' : 'bg-red-500';
  
  return (
    <div className="flex items-center p-4 hover:bg-slate-700/50 transition-colors">
      <input type="checkbox" className="mr-4" />
      
      <div className="flex items-center gap-2 w-24">
        <span className={`w-3 h-3 rounded-full ${confidenceColor}`} />
        <span>{Math.round(item.confidence * 100)}%</span>
      </div>
      
      <div className="flex-1">
        <p className="font-medium">{formatDocType(item.document_type)}</p>
        <p className="text-sm text-slate-400">{item.filename}</p>
      </div>
      
      <div className="w-32">
        <span className="px-3 py-1 rounded-full text-sm bg-slate-700">
          {item.category}
        </span>
      </div>
      
      <div className="w-32 text-right">
        {item.calculated_co2e_kg && (
          <span className="text-emerald-500 font-medium">
            {formatEmissions(item.calculated_co2e_kg)}
          </span>
        )}
      </div>
      
      <div className="w-40 flex gap-2 justify-end">
        {item.confidence >= 0.9 ? (
          <button 
            onClick={() => onApprove(item.id)}
            className="px-4 py-2 bg-emerald-500/20 text-emerald-500 rounded-lg hover:bg-emerald-500 hover:text-white transition-colors"
          >
            Approve
          </button>
        ) : (
          <button 
            onClick={() => onReview(item.id)}
            className="px-4 py-2 bg-yellow-500/20 text-yellow-500 rounded-lg hover:bg-yellow-500 hover:text-white transition-colors"
          >
            Review
          </button>
        )}
      </div>
    </div>
  );
}
```

## 🔐 Authentication Context

```tsx
// contexts/AuthContext.tsx
import { createContext, useContext, useState } from 'react';
import type { User, UserRole } from '@/api/types';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  
  const hasPermission = (permission: string) => {
    if (!user) return false;
    
    const permissions: Record<UserRole, string[]> = {
      admin: ['*'],
      supervisor: ['review', 'approve', 'export', 'analytics'],
      user: ['upload', 'view_own'],
    };
    
    return permissions[user.role].includes('*') || 
           permissions[user.role].includes(permission);
  };
  
  return (
    <AuthContext.Provider value={{ user, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext)!;
```

## 🎯 Backend Endpoints Reference

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Review** | GET `/api/v1/review/queue` | Get review queue |
| | GET `/api/v1/review/stats` | Dashboard statistics |
| | POST `/api/v1/review/queue/{id}/approve` | Approve item |
| | POST `/api/v1/review/queue/{id}/reject` | Reject item |
| | POST `/api/v1/review/queue/bulk-approve` | Bulk approve |
| **Smart** | POST `/api/v1/sustainability/smart/process` | Process document |
| | POST `/api/v1/sustainability/smart/process-auto` | Auto-learn process |
| **Email** | POST `/api/v1/email/test` | Test email processing |
| **Data** | GET `/api/v1/sustainability/db/companies` | Get companies |
| | GET `/api/v1/sustainability/db/footprints` | Carbon footprints |

## 🚀 Development

```bash
# Start frontend dev server
npm run dev

# Start backend (in separate terminal)
cd ../  # goai-platform-v1 root
uvicorn main:app --reload --port 8000
```

## 📦 Build

```bash
npm run build
npm run preview
```

---

Built with 💚 for the GoAI Sustainability Platform

