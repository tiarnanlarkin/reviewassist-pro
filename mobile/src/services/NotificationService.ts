import PushNotification, { Importance } from 'react-native-push-notification';
import { Platform, PermissionsAndroid } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export interface NotificationData {
  id: string;
  title: string;
  message: string;
  data?: any;
  type: 'review' | 'response' | 'alert' | 'system';
}

export class NotificationService {
  private static isInitialized = false;

  static async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      // Request permissions
      await this.requestPermissions();

      // Configure push notifications
      PushNotification.configure({
        onRegister: (token) => {
          console.log('Push notification token:', token);
          this.storePushToken(token.token);
        },

        onNotification: (notification) => {
          console.log('Notification received:', notification);
          this.handleNotification(notification);
        },

        onAction: (notification) => {
          console.log('Notification action:', notification);
          this.handleNotificationAction(notification);
        },

        onRegistrationError: (err) => {
          console.error('Push notification registration error:', err);
        },

        permissions: {
          alert: true,
          badge: true,
          sound: true,
        },

        popInitialNotification: true,
        requestPermissions: Platform.OS === 'ios',
      });

      // Create notification channels for Android
      if (Platform.OS === 'android') {
        this.createNotificationChannels();
      }

      this.isInitialized = true;
      console.log('NotificationService initialized successfully');
    } catch (error) {
      console.error('NotificationService initialization failed:', error);
      throw error;
    }
  }

  private static async requestPermissions(): Promise<boolean> {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
          {
            title: 'ReviewAssist Pro Notifications',
            message: 'Allow notifications to stay updated on new reviews and responses.',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          }
        );
        return granted === PermissionsAndroid.RESULTS.GRANTED;
      } catch (error) {
        console.error('Permission request failed:', error);
        return false;
      }
    }
    return true;
  }

  private static createNotificationChannels(): void {
    const channels = [
      {
        channelId: 'reviews',
        channelName: 'New Reviews',
        channelDescription: 'Notifications for new reviews',
        importance: Importance.HIGH,
        vibrate: true,
      },
      {
        channelId: 'responses',
        channelName: 'Response Updates',
        channelDescription: 'Notifications for response updates',
        importance: Importance.DEFAULT,
        vibrate: false,
      },
      {
        channelId: 'alerts',
        channelName: 'Urgent Alerts',
        channelDescription: 'Urgent notifications requiring immediate attention',
        importance: Importance.HIGH,
        vibrate: true,
      },
      {
        channelId: 'system',
        channelName: 'System Updates',
        channelDescription: 'System and app update notifications',
        importance: Importance.LOW,
        vibrate: false,
      },
    ];

    channels.forEach(channel => {
      PushNotification.createChannel(
        {
          channelId: channel.channelId,
          channelName: channel.channelName,
          channelDescription: channel.channelDescription,
          importance: channel.importance,
          vibrate: channel.vibrate,
        },
        (created) => {
          console.log(`Channel ${channel.channelId} created:`, created);
        }
      );
    });
  }

  static async setupUserNotifications(userId: string): Promise<void> {
    try {
      const pushToken = await AsyncStorage.getItem('pushToken');
      if (pushToken) {
        // Register push token with backend
        await this.registerPushToken(userId, pushToken);
      }
    } catch (error) {
      console.error('User notification setup failed:', error);
    }
  }

  private static async storePushToken(token: string): Promise<void> {
    try {
      await AsyncStorage.setItem('pushToken', token);
    } catch (error) {
      console.error('Failed to store push token:', error);
    }
  }

  private static async registerPushToken(userId: string, token: string): Promise<void> {
    try {
      // This would register the token with your backend
      // Implementation depends on your backend API
      console.log('Registering push token for user:', userId, token);
    } catch (error) {
      console.error('Failed to register push token:', error);
    }
  }

  static showLocalNotification(data: NotificationData): void {
    PushNotification.localNotification({
      id: data.id,
      title: data.title,
      message: data.message,
      channelId: data.type === 'review' ? 'reviews' : 
                 data.type === 'response' ? 'responses' :
                 data.type === 'alert' ? 'alerts' : 'system',
      importance: data.type === 'alert' ? 'high' : 'default',
      priority: data.type === 'alert' ? 'high' : 'default',
      vibrate: data.type === 'alert' || data.type === 'review',
      playSound: true,
      soundName: 'default',
      userInfo: data.data,
      actions: data.type === 'review' ? ['View', 'Respond'] : ['View'],
    });
  }

  static scheduleNotification(data: NotificationData, date: Date): void {
    PushNotification.localNotificationSchedule({
      id: data.id,
      title: data.title,
      message: data.message,
      date: date,
      channelId: data.type === 'review' ? 'reviews' : 
                 data.type === 'response' ? 'responses' :
                 data.type === 'alert' ? 'alerts' : 'system',
      userInfo: data.data,
    });
  }

  static cancelNotification(id: string): void {
    PushNotification.cancelLocalNotifications({ id });
  }

  static cancelAllNotifications(): void {
    PushNotification.cancelAllLocalNotifications();
  }

  static async clearNotifications(): Promise<void> {
    try {
      this.cancelAllNotifications();
      PushNotification.removeAllDeliveredNotifications();
      await AsyncStorage.removeItem('pushToken');
    } catch (error) {
      console.error('Failed to clear notifications:', error);
    }
  }

  static setBadgeNumber(number: number): void {
    if (Platform.OS === 'ios') {
      PushNotification.setApplicationIconBadgeNumber(number);
    }
  }

  static async getNotificationSettings(): Promise<any> {
    return new Promise((resolve) => {
      PushNotification.checkPermissions((permissions) => {
        resolve(permissions);
      });
    });
  }

  private static handleNotification(notification: any): void {
    console.log('Handling notification:', notification);
    
    // Handle notification based on type
    if (notification.userInfo) {
      const { type, data } = notification.userInfo;
      
      switch (type) {
        case 'review':
          this.handleReviewNotification(data);
          break;
        case 'response':
          this.handleResponseNotification(data);
          break;
        case 'alert':
          this.handleAlertNotification(data);
          break;
        default:
          console.log('Unknown notification type:', type);
      }
    }
  }

  private static handleNotificationAction(notification: any): void {
    console.log('Handling notification action:', notification);
    
    const { action, userInfo } = notification;
    
    switch (action) {
      case 'View':
        // Navigate to appropriate screen
        break;
      case 'Respond':
        // Navigate to response screen
        break;
      default:
        console.log('Unknown notification action:', action);
    }
  }

  private static handleReviewNotification(data: any): void {
    // Handle new review notification
    console.log('New review notification:', data);
  }

  private static handleResponseNotification(data: any): void {
    // Handle response notification
    console.log('Response notification:', data);
  }

  private static handleAlertNotification(data: any): void {
    // Handle alert notification
    console.log('Alert notification:', data);
  }
}

