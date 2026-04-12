package examples;

import java.sql.Connection;
import java.sql.DriverManager;
import java.io.File;
import java.io.FileWriter;

// 1. Interface Segregation Principle (ISP) Violation
// One massive interface forcing implementers to define methods they don't need.
interface ISuperWorker {
    void work();
    void eat();
    void sleep();
    void maintainServers();
}

// 2. Liskov Substitution Principle (LSP) Violation
// Square inherits from Rectangle but breaks the expected behavior of width/height independence.
class Rectangle {
    protected int w;
    protected int h;
    public void setW(int w) { this.w = w; }
    public void setH(int h) { this.h = h; }
    public int area() { return w * h; }
}

class Square extends Rectangle {
    public void setW(int w) { this.w = w; this.h = w; }
    public void setH(int h) { this.w = h; this.h = h; }
}

// 3. Single Responsibility Principle (SRP) Violation
// This God Class handles business logic, file I/O, database access, and implements workers.
public class BadCode implements ISuperWorker {
    
    // 4. Dependency Inversion Principle (DIP) Violation
    // Instantiating concrete dependencies directly instead of injecting abstractions.
    private Square sq = new Square();
    
    // CLEAN CODE VIOLATIONS: Public fields, terrible naming conventions
    public int typ; 
    public String dataString;

    public BadCode(int t) {
        typ = t;
    }

    // 5. Open/Closed Principle (OCP) Violation
    // Every time a new type is added, we have to come back and modify this method.
    public void doTypeStuff() {
        if(typ == 1) {
            System.out.println("type 1");
        } else if (typ == 2) {
            System.out.println("type 2");
        } else if (typ == 3) {
            System.out.println("type 3");
        } else {
            System.out.println("other");
        }
    }

    // CLEAN CODE VIOLATIONS: 
    // - Bad naming conventions (snake_case in Java, non-descriptive parameters `a`, `b`)
    // - Deep nesting (Arrow Anti-Pattern)
    // - Magic numbers (42, 3)
    // - Redundant boolean checks (isTrue == true)
    // - Swallowing exceptions
    // - Lying comments
    public void process_data_and_save(int a, int b, boolean isTrue) {
        // adds a and b together
        int c = a * b; // actually multiplies them!

        if (isTrue == true) { 
            if (c > 42) { 
                for(int i=0; i<3; i++) { 
                    try {
                        // Hardcoded DB credentials and connection logic mixed into business logic
                        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/db", "root", "password123");
                        conn.createStatement().execute("INSERT INTO table VALUES (" + c + ")");
                        
                        // Hardcoded platform-specific path that will crash on Mac/Linux
                        File f = new File("C:\\temp\\output.txt");
                        FileWriter fw = new FileWriter(f);
                        fw.write("result: " + c);
                        fw.close(); // Resource leak potential (not using try-with-resources)
                    } catch (Exception e) {
                        // Empty catch block: silently swallowing exceptions!
                    }
                }
            }
        }
    }

    // --- Forced implementations due to ISP violation ---
    public void work() {
        System.out.println("working");
    }

    public void eat() {
        // This class doesn't eat, but the fat interface forces us to implement it
        throw new RuntimeException("I don't eat");
    }

    public void sleep() {
        throw new RuntimeException("I don't sleep");
    }

    public void maintainServers() {
        System.out.println("maintaining");
    }
}