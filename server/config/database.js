const mongoose = require('mongoose');

const connectDB = async () => {
    try {
        // MongoDB connection options
        const options = {
            // Use new URL parser
            useNewUrlParser: true,
            useUnifiedTopology: true,
 feat/auth-error-handling-5447018483623698560

            // Connection pool settings
            maxPoolSize: 10,
            minPoolSize: 2,

            // Timeout settings
            serverSelectionTimeoutMS: 5000,
            socketTimeoutMS: 45000,

            // Retry settings
            retryWrites: true,
            retryReads: true,

            // Authentication
            authSource: 'admin'
        };

        // Get MongoDB URI from environment
        const mongoURI = process.env.MONGODB_URI || process.env.DATABASE_URL;


            
            // Connection pool settings
            maxPoolSize: 10,
            minPoolSize: 2,
            
            // Timeout settings
            serverSelectionTimeoutMS: 5000,
            socketTimeoutMS: 45000,
            
            // Retry settings
            retryWrites: true,
            retryReads: true,
            
            // Authentication
            authSource: 'admin'
        };
        
        // Get MongoDB URI from environment
        const mongoURI = process.env.MONGODB_URI || process.env.DATABASE_URL;
        
 main
        if (!mongoURI) {
            console.warn('⚠️  No MongoDB URI found. Running without database.');
            console.warn('   Set MONGODB_URI in your .env file to enable database features.');
            return;
        }
 feat/auth-error-handling-5447018483623698560

        // Connect to MongoDB
        const conn = await mongoose.connect(mongoURI, options);

        console.log(`✅ MongoDB Connected: ${conn.connection.host}`);
        console.log(`   Database: ${conn.connection.name}`);


        
        // Connect to MongoDB
        const conn = await mongoose.connect(mongoURI, options);
        
        console.log(`✅ MongoDB Connected: ${conn.connection.host}`);
        console.log(`   Database: ${conn.connection.name}`);
        
 main
        // Connection event handlers
        mongoose.connection.on('error', (err) => {
            console.error('❌ MongoDB connection error:', err);
        });
 feat/auth-error-handling-5447018483623698560

        mongoose.connection.on('disconnected', () => {
            console.warn('⚠️  MongoDB disconnected');
        });

        mongoose.connection.on('reconnected', () => {
            console.log('✅ MongoDB reconnected');
        });


        
        mongoose.connection.on('disconnected', () => {
            console.warn('⚠️  MongoDB disconnected');
        });
        
        mongoose.connection.on('reconnected', () => {
            console.log('✅ MongoDB reconnected');
        });
        
 main
        // Graceful shutdown
        process.on('SIGINT', async () => {
            await mongoose.connection.close();
            console.log('\n🔌 MongoDB connection closed through app termination');
            process.exit(0);
        });
 feat/auth-error-handling-5447018483623698560

    } catch (error) {
        console.error('❌ MongoDB connection error:', error.message);


        
    } catch (error) {
        console.error('❌ MongoDB connection error:', error.message);
        
 main
        // In development, continue without database
        if (process.env.NODE_ENV === 'development') {
            console.warn('⚠️  Running in development mode without database');
        } else {
            // In production, exit on database error
            process.exit(1);
        }
    }
};

 feat/auth-error-handling-5447018483623698560
module.exports = connectDB;

module.exports = connectDB;
 main
