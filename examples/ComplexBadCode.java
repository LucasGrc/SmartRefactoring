package examples;

import java.sql.*;
import java.io.*;
import java.util.*;
import java.net.*;

// GOD CLASS: handles users, orders, payments, emails, reports, and inventory
// SRP, DIP, ISP, OCP all violated in one place
public class ComplexBadCode {

    // ISP violation: one fat interface for everything
    interface SystemManager {
        void manageUsers();
        void processOrders();
        void sendEmails();
        void generateReports();
        void manageInventory();
        void processPayments();
        void handleRefunds();
        void logActivity();
    }

    // DIP violation: concrete dependencies hardcoded everywhere
    private Connection dbConn;
    private String smtpServer = "smtp.company.com";
    private String reportPath = "C:\\reports\\";

    // Terrible naming, public mutable state
    public List data = new ArrayList();
    public Map mp = new HashMap();
    public int x, y, z;
    public boolean f1, f2, f3;
    public String s1, s2, s3;

    // LSP violation: subclasses break parent contracts
    static class Animal {
        public String makeSound() { return "..."; }
        public void fly() { throw new RuntimeException("Cannot fly"); }
        public void swim() { throw new RuntimeException("Cannot swim"); }
        public void run() { throw new RuntimeException("Cannot run"); }
    }

    static class Dog extends Animal {
        public String makeSound() { return "woof"; }
        public void swim() { System.out.println("dog swims"); }
        public void run() { System.out.println("dog runs"); }
        // fly() still throws — LSP broken
    }

    static class Eagle extends Animal {
        public String makeSound() { return "screech"; }
        public void fly() { System.out.println("eagle flies"); }
        // swim() and run() still throw — LSP broken
    }

    static class Penguin extends Animal {
        public String makeSound() { return "squawk"; }
        public void swim() { System.out.println("penguin swims"); }
        // fly() still throws, run() throws — LSP broken
    }

    // OCP violation: new discount type = modify this method
    public double calculateDiscount(String customerType, double amount) {
        if (customerType.equals("VIP")) {
            return amount * 0.2;
        } else if (customerType.equals("REGULAR")) {
            return amount * 0.1;
        } else if (customerType.equals("NEW")) {
            return amount * 0.05;
        } else if (customerType.equals("EMPLOYEE")) {
            return amount * 0.3;
        } else if (customerType.equals("STUDENT")) {
            return amount * 0.15;
        } else if (customerType.equals("SENIOR")) {
            return amount * 0.12;
        } else {
            return 0;
        }
    }

    // OCP violation: new status = modify this method
    public String getOrderStatus(int code) {
        if (code == 1) return "pending";
        else if (code == 2) return "processing";
        else if (code == 3) return "shipped";
        else if (code == 4) return "delivered";
        else if (code == 5) return "cancelled";
        else if (code == 6) return "refunded";
        else return "unknown";
    }

    // SRP + DIP + all clean code violations:
    // - snake_case naming
    // - magic numbers
    // - deep nesting (arrow anti-pattern)
    // - empty catch blocks
    // - hardcoded credentials
    // - lying comment
    // - flag parameters
    // - too many responsibilities
    public void process_user_order(int uid, int oid, boolean isPremium, boolean sendEmail, boolean saveReport) {
        // subtracts order from inventory
        int total = 0;
        try {
            // hardcoded credentials
            dbConn = DriverManager.getConnection("jdbc:mysql://localhost/shop", "admin", "admin123");
            ResultSet rs = dbConn.createStatement().executeQuery("SELECT * FROM orders WHERE id=" + oid);
            if (rs.next()) {
                total = rs.getInt("amount") * rs.getInt("qty"); // actually multiplies!
                if (total > 0) {
                    if (isPremium) {
                        if (total > 1000) {
                            total = (int)(total * 0.8);
                            if (sendEmail) {
                                try {
                                    // raw socket email
                                    Socket sock = new Socket("smtp.company.com", 25);
                                    PrintWriter pw = new PrintWriter(sock.getOutputStream());
                                    pw.println("MAIL FROM: orders@company.com");
                                    pw.println("RCPT TO: user" + uid + "@company.com");
                                    pw.println("DATA");
                                    pw.println("Your premium order total: " + total);
                                    pw.println(".");
                                    pw.flush();
                                    sock.close();
                                } catch (Exception e) {} // swallowed!
                            }
                            if (saveReport) {
                                try {
                                    FileWriter fw = new FileWriter("C:\\reports\\order_" + oid + ".txt");
                                    fw.write("uid:" + uid + " total:" + total);
                                    fw.close(); // no try-with-resources
                                } catch (Exception e) {} // swallowed!
                            }
                        } else {
                            total = (int)(total * 0.9);
                        }
                    } else {
                        total = (int)(total * 0.95);
                    }
                    dbConn.createStatement().execute("UPDATE inventory SET qty=qty-1 WHERE order_id=" + oid);
                    dbConn.createStatement().execute("INSERT INTO payments VALUES(" + uid + "," + total + ")");
                }
            }
        } catch (Exception e) {
            // silent failure
        }
    }

    // DRY violation: copy-paste of nearly identical validation logic
    public boolean validateUserEmail(String email) {
        if (email == null) return false;
        if (email.length() == 0) return false;
        if (!email.contains("@")) return false;
        if (!email.contains(".")) return false;
        if (email.length() > 255) return false;
        return true;
    }

    public boolean validateAdminEmail(String email) {
        if (email == null) return false;
        if (email.length() == 0) return false;
        if (!email.contains("@")) return false;
        if (!email.contains(".")) return false;
        if (email.length() > 255) return false;
        return true;
    }

    public boolean validateSupportEmail(String email) {
        if (email == null) return false;
        if (email.length() == 0) return false;
        if (!email.contains("@")) return false;
        if (!email.contains(".")) return false;
        if (email.length() > 255) return false;
        return true;
    }

    // SRP violation: report generation mixed with data access and formatting
    // Magic numbers, terrible naming
    public void gen_rpt(int t) {
        try {
            dbConn = DriverManager.getConnection("jdbc:mysql://localhost/shop", "admin", "admin123");
            ResultSet rs;
            if (t == 1) {
                rs = dbConn.createStatement().executeQuery("SELECT * FROM sales WHERE month=1");
            } else if (t == 2) {
                rs = dbConn.createStatement().executeQuery("SELECT * FROM sales WHERE month=2");
            } else if (t == 3) {
                rs = dbConn.createStatement().executeQuery("SELECT * FROM sales WHERE month=3");
            } else {
                rs = dbConn.createStatement().executeQuery("SELECT * FROM sales");
            }
            StringBuilder sb = new StringBuilder();
            while (rs.next()) {
                sb.append(rs.getString(1)).append(",").append(rs.getString(2)).append("\n");
            }
            FileWriter fw = new FileWriter("C:\\reports\\report_" + t + ".csv");
            fw.write(sb.toString());
            fw.close();
        } catch (Exception e) {}
    }

    // Flag parameter + SRP + naming violations
    public void handleU(String nm, String em, int ag, boolean isNew, boolean isBanned, boolean isAdmin) {
        if (isNew) {
            System.out.println("new user: " + nm);
            try {
                dbConn = DriverManager.getConnection("jdbc:mysql://localhost/shop", "admin", "admin123");
                dbConn.createStatement().execute("INSERT INTO users VALUES('" + nm + "','" + em + "'," + ag + ")");
            } catch (Exception e) {}
        } else if (isBanned) {
            System.out.println("banned: " + nm);
            try {
                dbConn = DriverManager.getConnection("jdbc:mysql://localhost/shop", "admin", "admin123");
                dbConn.createStatement().execute("UPDATE users SET banned=1 WHERE email='" + em + "'");
            } catch (Exception e) {}
        } else if (isAdmin) {
            System.out.println("admin: " + nm);
            try {
                dbConn = DriverManager.getConnection("jdbc:mysql://localhost/shop", "admin", "admin123");
                dbConn.createStatement().execute("UPDATE users SET role='admin' WHERE email='" + em + "'");
            } catch (Exception e) {}
        }
    }

    // Redundant comments, bad naming, magic numbers
    public int calc(int a, int b, int c) {
        // multiply a by b
        int r1 = a * b;
        // add c
        int r2 = r1 + c;
        // check if greater than 500
        if (r2 > 500) {
            // apply 15% reduction
            r2 = (int)(r2 * 0.85);
        }
        // check if greater than 1000
        if (r2 > 1000) {
            // apply another reduction
            r2 = (int)(r2 * 0.75);
        }
        // return result
        return r2;
    }

    // Dead code + unused variables
    public void unusedStuff() {
        int unused1 = 99;
        String unused2 = "dead code";
        List unused3 = new ArrayList();
        // This method is never called
        System.out.println("this never runs");
    }

    // Forced ISP implementations that make no sense for this class
    public void manageUsers() { System.out.println("managing users"); }
    public void processOrders() { System.out.println("processing orders"); }
    public void sendEmails() { System.out.println("sending emails"); }
    public void generateReports() { System.out.println("generating reports"); }
    public void manageInventory() { System.out.println("managing inventory"); }
    public void processPayments() { System.out.println("processing payments"); }
    public void handleRefunds() { System.out.println("handling refunds"); }
    public void logActivity() { System.out.println("logging"); }
}