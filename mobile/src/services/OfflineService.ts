import SQLite from 'react-native-sqlite-storage';
import NetInfo from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Enable debugging
SQLite.DEBUG(true);
SQLite.enablePromise(true);

export interface OfflineAction {
  id: string;
  type: 'CREATE' | 'UPDATE' | 'DELETE';
  endpoint: string;
  data: any;
  timestamp: number;
  retryCount: number;
}

export interface CachedData {
  key: string;
  data: any;
  timestamp: number;
  expiry?: number;
}

export class OfflineService {
  private static db: SQLite.SQLiteDatabase | null = null;
  private static isInitialized = false;
  private static syncQueue: OfflineAction[] = [];
  private static isOnline = true;

  static async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      // Initialize SQLite database
      await this.initializeDatabase();
      
      // Setup network monitoring
      this.setupNetworkMonitoring();
      
      // Load pending actions from storage
      await this.loadPendingActions();
      
      this.isInitialized = true;
      console.log('OfflineService initialized successfully');
    } catch (error) {
      console.error('OfflineService initialization failed:', error);
      throw error;
    }
  }

  private static async initializeDatabase(): Promise<void> {
    try {
      this.db = await SQLite.openDatabase({
        name: 'ReviewAssistPro.db',
        location: 'default',
      });

      // Create tables
      await this.createTables();
      console.log('SQLite database initialized');
    } catch (error) {
      console.error('Database initialization failed:', error);
      throw error;
    }
  }

  private static async createTables(): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const tables = [
      // Cached data table
      `CREATE TABLE IF NOT EXISTS cached_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cache_key TEXT UNIQUE NOT NULL,
        data TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        expiry INTEGER
      )`,
      
      // Offline actions queue
      `CREATE TABLE IF NOT EXISTS offline_actions (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        data TEXT NOT NULL,
        timestamp INTEGER NOT NULL,
        retry_count INTEGER DEFAULT 0
      )`,
      
      // Reviews cache
      `CREATE TABLE IF NOT EXISTS reviews_cache (
        id TEXT PRIMARY KEY,
        reviewer_name TEXT,
        platform TEXT,
        rating INTEGER,
        review_text TEXT,
        sentiment TEXT,
        status TEXT,
        response_time TEXT,
        created_at TEXT,
        updated_at TEXT,
        is_synced INTEGER DEFAULT 0
      )`,
      
      // User preferences
      `CREATE TABLE IF NOT EXISTS user_preferences (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
      )`
    ];

    for (const table of tables) {
      await this.db.executeSql(table);
    }
  }

  private static setupNetworkMonitoring(): void {
    NetInfo.addEventListener(state => {
      const wasOnline = this.isOnline;
      this.isOnline = state.isConnected ?? false;
      
      console.log('Network state changed:', {
        isConnected: state.isConnected,
        type: state.type,
        isInternetReachable: state.isInternetReachable,
      });

      // If we just came back online, sync pending actions
      if (!wasOnline && this.isOnline) {
        this.syncPendingActions();
      }
    });
  }

  static async isNetworkAvailable(): Promise<boolean> {
    const state = await NetInfo.fetch();
    return state.isConnected ?? false;
  }

  // Cache Management
  static async cacheData(key: string, data: any, expiryMinutes?: number): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const timestamp = Date.now();
    const expiry = expiryMinutes ? timestamp + (expiryMinutes * 60 * 1000) : null;

    try {
      await this.db.executeSql(
        'INSERT OR REPLACE INTO cached_data (cache_key, data, timestamp, expiry) VALUES (?, ?, ?, ?)',
        [key, JSON.stringify(data), timestamp, expiry]
      );
    } catch (error) {
      console.error('Failed to cache data:', error);
      throw error;
    }
  }

  static async getCachedData(key: string): Promise<any | null> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const results = await this.db.executeSql(
        'SELECT data, timestamp, expiry FROM cached_data WHERE cache_key = ?',
        [key]
      );

      if (results[0].rows.length === 0) {
        return null;
      }

      const row = results[0].rows.item(0);
      const now = Date.now();

      // Check if data has expired
      if (row.expiry && now > row.expiry) {
        await this.clearCachedData(key);
        return null;
      }

      return JSON.parse(row.data);
    } catch (error) {
      console.error('Failed to get cached data:', error);
      return null;
    }
  }

  static async clearCachedData(key: string): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      await this.db.executeSql('DELETE FROM cached_data WHERE cache_key = ?', [key]);
    } catch (error) {
      console.error('Failed to clear cached data:', error);
    }
  }

  static async clearExpiredCache(): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    const now = Date.now();
    try {
      await this.db.executeSql('DELETE FROM cached_data WHERE expiry IS NOT NULL AND expiry < ?', [now]);
    } catch (error) {
      console.error('Failed to clear expired cache:', error);
    }
  }

  // Offline Actions Queue
  static async queueAction(action: Omit<OfflineAction, 'id' | 'timestamp' | 'retryCount'>): Promise<void> {
    const offlineAction: OfflineAction = {
      ...action,
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      retryCount: 0,
    };

    this.syncQueue.push(offlineAction);
    await this.saveActionToDatabase(offlineAction);

    // Try to sync immediately if online
    if (this.isOnline) {
      this.syncPendingActions();
    }
  }

  private static async saveActionToDatabase(action: OfflineAction): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      await this.db.executeSql(
        'INSERT INTO offline_actions (id, type, endpoint, data, timestamp, retry_count) VALUES (?, ?, ?, ?, ?, ?)',
        [action.id, action.type, action.endpoint, JSON.stringify(action.data), action.timestamp, action.retryCount]
      );
    } catch (error) {
      console.error('Failed to save action to database:', error);
    }
  }

  private static async loadPendingActions(): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const results = await this.db.executeSql('SELECT * FROM offline_actions ORDER BY timestamp ASC');
      
      this.syncQueue = [];
      for (let i = 0; i < results[0].rows.length; i++) {
        const row = results[0].rows.item(i);
        this.syncQueue.push({
          id: row.id,
          type: row.type,
          endpoint: row.endpoint,
          data: JSON.parse(row.data),
          timestamp: row.timestamp,
          retryCount: row.retry_count,
        });
      }

      console.log(`Loaded ${this.syncQueue.length} pending actions`);
    } catch (error) {
      console.error('Failed to load pending actions:', error);
    }
  }

  static async syncPendingActions(): Promise<void> {
    if (!this.isOnline || this.syncQueue.length === 0) {
      return;
    }

    console.log(`Syncing ${this.syncQueue.length} pending actions`);

    const actionsToSync = [...this.syncQueue];
    
    for (const action of actionsToSync) {
      try {
        await this.executeAction(action);
        await this.removeActionFromQueue(action.id);
      } catch (error) {
        console.error('Failed to sync action:', action.id, error);
        await this.incrementRetryCount(action.id);
      }
    }
  }

  private static async executeAction(action: OfflineAction): Promise<void> {
    // This would execute the actual API call
    // Implementation depends on your API structure
    console.log('Executing action:', action);
    
    // Simulate API call
    const response = await fetch(action.endpoint, {
      method: action.type === 'CREATE' ? 'POST' : 
              action.type === 'UPDATE' ? 'PUT' : 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        // Add authentication headers here
      },
      body: action.type !== 'DELETE' ? JSON.stringify(action.data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.status}`);
    }
  }

  private static async removeActionFromQueue(actionId: string): Promise<void> {
    this.syncQueue = this.syncQueue.filter(action => action.id !== actionId);
    
    if (this.db) {
      try {
        await this.db.executeSql('DELETE FROM offline_actions WHERE id = ?', [actionId]);
      } catch (error) {
        console.error('Failed to remove action from database:', error);
      }
    }
  }

  private static async incrementRetryCount(actionId: string): Promise<void> {
    const action = this.syncQueue.find(a => a.id === actionId);
    if (action) {
      action.retryCount++;
      
      // Remove action if retry count exceeds limit
      if (action.retryCount >= 3) {
        await this.removeActionFromQueue(actionId);
        console.log('Action removed due to max retries:', actionId);
      } else if (this.db) {
        try {
          await this.db.executeSql(
            'UPDATE offline_actions SET retry_count = ? WHERE id = ?',
            [action.retryCount, actionId]
          );
        } catch (error) {
          console.error('Failed to update retry count:', error);
        }
      }
    }
  }

  // Reviews Cache Management
  static async cacheReviews(reviews: any[]): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      // Clear existing cache
      await this.db.executeSql('DELETE FROM reviews_cache');
      
      // Insert new reviews
      for (const review of reviews) {
        await this.db.executeSql(
          `INSERT INTO reviews_cache 
           (id, reviewer_name, platform, rating, review_text, sentiment, status, response_time, created_at, updated_at, is_synced) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            review.id || `temp_${Date.now()}_${Math.random()}`,
            review.reviewer_name,
            review.platform,
            review.rating,
            review.review_text,
            review.sentiment,
            review.status,
            review.response_time,
            review.created_at,
            review.updated_at || new Date().toISOString(),
            1 // is_synced
          ]
        );
      }
    } catch (error) {
      console.error('Failed to cache reviews:', error);
      throw error;
    }
  }

  static async getCachedReviews(): Promise<any[]> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const results = await this.db.executeSql('SELECT * FROM reviews_cache ORDER BY created_at DESC');
      
      const reviews = [];
      for (let i = 0; i < results[0].rows.length; i++) {
        reviews.push(results[0].rows.item(i));
      }
      
      return reviews;
    } catch (error) {
      console.error('Failed to get cached reviews:', error);
      return [];
    }
  }

  // User Preferences
  static async setUserPreference(key: string, value: any): Promise<void> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      await this.db.executeSql(
        'INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)',
        [key, JSON.stringify(value)]
      );
    } catch (error) {
      console.error('Failed to set user preference:', error);
    }
  }

  static async getUserPreference(key: string, defaultValue?: any): Promise<any> {
    if (!this.db) {
      throw new Error('Database not initialized');
    }

    try {
      const results = await this.db.executeSql('SELECT value FROM user_preferences WHERE key = ?', [key]);
      
      if (results[0].rows.length === 0) {
        return defaultValue;
      }
      
      return JSON.parse(results[0].rows.item(0).value);
    } catch (error) {
      console.error('Failed to get user preference:', error);
      return defaultValue;
    }
  }

  // Cleanup
  static async cleanup(): Promise<void> {
    try {
      await this.clearExpiredCache();
      console.log('Offline service cleanup completed');
    } catch (error) {
      console.error('Cleanup failed:', error);
    }
  }

  static async reset(): Promise<void> {
    if (!this.db) {
      return;
    }

    try {
      await this.db.executeSql('DELETE FROM cached_data');
      await this.db.executeSql('DELETE FROM offline_actions');
      await this.db.executeSql('DELETE FROM reviews_cache');
      await this.db.executeSql('DELETE FROM user_preferences');
      
      this.syncQueue = [];
      console.log('Offline service reset completed');
    } catch (error) {
      console.error('Reset failed:', error);
    }
  }
}

