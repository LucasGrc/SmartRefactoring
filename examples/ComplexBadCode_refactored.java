package examples;

import java.sql.*;
import java.io.*;
import java.util.*;

public interface DatabaseConnection {
  Connection getConnection() throws SQLException;
}

class MySQLConnection implements DatabaseConnection {
  private final String url;
  private final String username;
  private final String password;

  public MySQLConnection(String url, String username, String password) {
    this.url = url;
    this.username = username;
    this.password = password;
  }

  @Override
  public Connection getConnection() throws SQLException {
    return DriverManager.getConnection(url, username, password);
  }
}

public interface EmailService {
  void sendEmail(String recipient, String subject, String message) throws Exception;
}

class SimpleEmailService implements EmailService {
  private final String smtpServer;
  private final int smtpPort;

  public SimpleEmailService(String smtpServer, int smtpPort) {
    this.smtpServer = smtpServer;
    this.smtpPort = smtpPort;
  }

  @Override
  public void sendEmail(String recipient, String subject, String message) throws Exception {
    try (java.net.Socket socket = new java.net.Socket(smtpServer, smtpPort)) {
      PrintWriter writer = new PrintWriter(socket.getOutputStream());
      writer.println("MAIL FROM: orders@company.com");
      writer.println("RCPT TO: " + recipient);
      writer.println("DATA");
      writer.println("Subject: " + subject);
      writer.println(message);
      writer.println(".");
      writer.flush();
    }
  }
}

public interface ReportGenerator {
  void generateReport(String filename, String content) throws IOException;
}

class FileReportGenerator implements ReportGenerator {
  private final String reportDirectory;

  public FileReportGenerator(String reportDirectory) {
    this.reportDirectory = reportDirectory;
  }

  @Override
  public void generateReport(String filename, String content) throws IOException {
    try (FileWriter writer = new FileWriter(reportDirectory + filename)) {
      writer.write(content);
    }
  }
}

public interface Animal {
  String makeSound();
}

public interface Flyable {
  void fly();
}

public interface Swimmable {
  void swim();
}

public interface Runnable {
  void run();
}

class Dog implements Animal, Swimmable, Runnable {
  @Override
  public String makeSound() {
    return "woof";
  }

  @Override
  public void swim() {
    System.out.println("dog swims");
  }

  @Override
  public void run() {
    System.out.println("dog runs");
  }
}

class Eagle implements Animal, Flyable {
  @Override
  public String makeSound() {
    return "screech";
  }

  @Override
  public void fly() {
    System.out.println("eagle flies");
  }
}

class Penguin implements Animal, Swimmable {
  @Override
  public String makeSound() {
    return "squawk";
  }

  @Override
  public void swim() {
    System.out.println("penguin swims");
  }
}

public interface DiscountStrategy {
  double calculateDiscount(double amount);
}

class VipDiscountStrategy implements DiscountStrategy {
  private static final double VIP_DISCOUNT_RATE = 0.2;

  @Override
  public double calculateDiscount(double amount) {
    return amount * VIP_DISCOUNT_RATE;
  }
}

class RegularDiscountStrategy implements DiscountStrategy {
  private static final double REGULAR_DISCOUNT_RATE = 0.1;

  @Override
  public double calculateDiscount(double amount) {
    return amount * REGULAR_DISCOUNT_RATE;
  }
}

class NewCustomerDiscountStrategy implements DiscountStrategy {
  private static final double NEW_CUSTOMER_DISCOUNT_RATE = 0.05;

  @Override
  public double calculateDiscount(double amount) {
    return amount * NEW_CUSTOMER_DISCOUNT_RATE;
  }
}

class EmployeeDiscountStrategy implements DiscountStrategy {
  private static final double EMPLOYEE_DISCOUNT_RATE = 0.3;

  @Override
  public double calculateDiscount(double amount) {
    return amount * EMPLOYEE_DISCOUNT_RATE;
  }
}

class StudentDiscountStrategy implements DiscountStrategy {
  private static final double STUDENT_DISCOUNT_RATE = 0.15;

  @Override
  public double calculateDiscount(double amount) {
    return amount * STUDENT_DISCOUNT_RATE;
  }
}

class SeniorDiscountStrategy implements DiscountStrategy {
  private static final double SENIOR_DISCOUNT_RATE = 0.12;

  @Override
  public double calculateDiscount(double amount) {
    return amount * SENIOR_DISCOUNT_RATE;
  }
}

class NoDiscountStrategy implements DiscountStrategy {
  @Override
  public double calculateDiscount(double amount) {
    return 0;
  }
}

public class DiscountCalculator {
  private final Map<String, DiscountStrategy> strategies = new HashMap<>();

  public DiscountCalculator() {
    strategies.put("VIP", new VipDiscountStrategy());
    strategies.put("REGULAR", new RegularDiscountStrategy());
    strategies.put("NEW", new NewCustomerDiscountStrategy());
    strategies.put("EMPLOYEE", new EmployeeDiscountStrategy());
    strategies.put("STUDENT", new StudentDiscountStrategy());
    strategies.put("SENIOR", new SeniorDiscountStrategy());
  }

  public double calculateDiscount(String customerType, double amount) {
    return strategies.getOrDefault(customerType, new NoDiscountStrategy())
        .calculateDiscount(amount);
  }
}

public enum OrderStatus {
  PENDING(1, "pending"),
  PROCESSING(2, "processing"),
  SHIPPED(3, "shipped"),
  DELIVERED(4, "delivered"),
  CANCELLED(5, "cancelled"),
  REFUNDED(6, "refunded");

  private final int code;
  private final String description;

  OrderStatus(int code, String description) {
    this.code = code;
    this.description = description;
  }

  public static String getStatusDescription(int code) {
    for (OrderStatus status : values()) {
      if (status.code == code) {
        return status.description;
      }
    }
    return "unknown";
  }
}

public class EmailValidator {
  private static final int MAXIMUM_EMAIL_LENGTH = 255;

  public boolean isValidEmail(String email) {
    if (email == null || email.length() == 0) {
      return false;
    }
    if (email.length() > MAXIMUM_EMAIL_LENGTH) {
      return false;
    }
    return email.contains("@") && email.contains(".");
  }
}

public class OrderData {
  private final int orderId;
  private final int amount;
  private final int quantity;

  public OrderData(int orderId, int amount, int quantity) {
    this.orderId = orderId;
    this.amount = amount;
    this.quantity = quantity;
  }

  public int getOrderId() {
    return orderId;
  }

  public int getAmount() {
    return amount;
  }

  public int getQuantity() {
    return quantity;
  }

  public int calculateTotal() {
    return amount * quantity;
  }
}

public interface OrderRepository {
  OrderData findOrderById(int orderId) throws SQLException;
  void updateInventory(int orderId) throws SQLException;
  void recordPayment(int userId, int amount) throws SQLException;
}

class DatabaseOrderRepository implements OrderRepository {
  private final DatabaseConnection databaseConnection;

  public DatabaseOrderRepository(DatabaseConnection databaseConnection) {
    this.databaseConnection = databaseConnection;
  }

  @Override
  public OrderData findOrderById(int orderId) throws SQLException {
    String query = "SELECT id, amount, qty FROM orders WHERE id = ?";
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {
      statement.setInt(1, orderId);
      try (ResultSet resultSet = statement.executeQuery()) {
        if (resultSet.next()) {
          return new OrderData(
              resultSet.getInt("id"),
              resultSet.getInt("amount"),
              resultSet.getInt("qty")
          );
        }
        return null;
      }
    }
  }

  @Override
  public void updateInventory(int orderId) throws SQLException {
    String query = "UPDATE inventory SET qty = qty - 1 WHERE order_id = ?";
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {
      statement.setInt(1, orderId);
      statement.execute();
    }
  }

  @Override
  public void recordPayment(int userId, int amount) throws SQLException {
    String query = "INSERT INTO payments (user_id, amount) VALUES (?, ?)";
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {
      statement.setInt(1, userId);
      statement.setInt(2, amount);
      statement.execute();
    }
  }
}

public class PremiumOrderProcessor {
  private static final double LARGE_ORDER_DISCOUNT_RATE = 0.8;
  private static final double REGULAR_PREMIUM_DISCOUNT_RATE = 0.9;
  private static final int LARGE_ORDER_THRESHOLD = 1000;

  public int calculatePremiumOrderTotal(int baseTotal) {
    if (baseTotal > LARGE_ORDER_THRESHOLD) {
      return (int) (baseTotal * LARGE_ORDER_DISCOUNT_RATE);
    }
    return (int) (baseTotal * REGULAR_PREMIUM_DISCOUNT_RATE);
  }
}

public class OrderProcessor {
  private static final double NON_PREMIUM_DISCOUNT_RATE = 0.95;

  private final OrderRepository orderRepository;
  private final EmailService emailService;
  private final ReportGenerator reportGenerator;
  private final PremiumOrderProcessor premiumOrderProcessor;

  public OrderProcessor(OrderRepository orderRepository,
                        EmailService emailService,
                        ReportGenerator reportGenerator,
                        PremiumOrderProcessor premiumOrderProcessor) {
    this.orderRepository = orderRepository;
    this.emailService = emailService;
    this.reportGenerator = reportGenerator;
    this.premiumOrderProcessor = premiumOrderProcessor;
  }

  public void processUserOrder(int userId, int orderId, boolean isPremium) throws Exception {
    OrderData order = orderRepository.findOrderById(orderId);
    if (order == null) {
      return;
    }

    int total = order.calculateTotal();
    if (total <= 0) {
      return;
    }

    int finalTotal = isPremium
        ? premiumOrderProcessor.calculatePremiumOrderTotal(total)
        : (int) (total * NON_PREMIUM_DISCOUNT_RATE);

    orderRepository.updateInventory(orderId);
    orderRepository.recordPayment(userId, finalTotal);
  }

  public void sendOrderConfirmationEmail(int userId, int orderId, int total) throws Exception {
    String recipient = "user" + userId + "@company.com";
    String subject = "Order Confirmation";
    String message = "Your order total: " + total;
    emailService.sendEmail(recipient, subject, message);
  }

  public void generateOrderReport(int orderId, int userId, int total) throws IOException {
    String filename = "order_" + orderId + ".txt";
    String content = "userId:" + userId + " total:" + total;
    reportGenerator.generateReport(filename, content);
  }
}

public interface UserRepository {
  void createUser(String name, String email, int age) throws SQLException;
  void banUser(String email) throws SQLException;
  void promoteToAdmin(String email) throws SQLException;
}

class DatabaseUserRepository implements UserRepository {
  private final DatabaseConnection databaseConnection;

  public DatabaseUserRepository(DatabaseConnection databaseConnection) {
    this.databaseConnection = databaseConnection;
  }

  @Override
  public void createUser(String name, String email, int age) throws SQLException {
    String query = "INSERT INTO users (name, email, age) VALUES (?, ?, ?)";
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {
      statement.setString(1, name);
      statement.setString(2, email);
      statement.setInt(3, age);
      statement.execute();
    }
  }

  @Override
  public void banUser(String email) throws SQLException {
    String query = "UPDATE users SET banned = 1 WHERE email = ?";
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {
      statement.setString(1, email);
      statement.execute();
    }
  }

  @Override
  public void promoteToAdmin(String email) throws SQLException {
    String query = "UPDATE users SET role = 'admin' WHERE email = ?";
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {
      statement.setString(1, email);
      statement.execute();
    }
  }
}

public class UserService {
  private final UserRepository userRepository;

  public UserService(UserRepository userRepository) {
    this.userRepository = userRepository;
  }

  public void createNewUser(String name, String email, int age) throws SQLException {
    System.out.println("new user: " + name);
    userRepository.createUser(name, email, age);
  }

  public void banUser(String name, String email) throws SQLException {
    System.out.println("banned: " + name);
    userRepository.banUser(email);
  }

  public void promoteUserToAdmin(String name, String email) throws SQLException {
    System.out.println("admin: " + name);
    userRepository.promoteToAdmin(email);
  }
}

public interface SalesRepository {
  List<String> getSalesDataForMonth(int month) throws SQLException;
  List<String> getAllSalesData() throws SQLException;
}

class DatabaseSalesRepository implements SalesRepository {
  private final DatabaseConnection databaseConnection;

  public DatabaseSalesRepository(DatabaseConnection databaseConnection) {
    this.databaseConnection = databaseConnection;
  }

  @Override
  public List<String> getSalesDataForMonth(int month) throws SQLException {
    String query = "SELECT * FROM sales WHERE month = ?";
    return executeSalesQuery(query, month);
  }

  @Override
  public List<String> getAllSalesData() throws SQLException {
    String query = "SELECT * FROM sales";
    return executeSalesQuery(query, null);
  }

  private List<String> executeSalesQuery(String query, Integer month) throws SQLException {
    List<String> results = new ArrayList<>();
    try (Connection connection = databaseConnection.getConnection();
         PreparedStatement statement = connection.prepareStatement(query)) {

      if (month != null) {
        statement.setInt(1, month);
      }

      try (ResultSet resultSet = statement.executeQuery()) {
        while (resultSet.next()) {
          String row = resultSet.getString(1) + "," + resultSet.getString(2);
          results.add(row);
        }
      }
    }
    return results;
  }
}

public class SalesReportService {
  private final SalesRepository salesRepository;
  private final ReportGenerator reportGenerator;

  public SalesReportService(SalesRepository salesRepository, ReportGenerator reportGenerator) {
    this.salesRepository = salesRepository;
    this.reportGenerator = reportGenerator;
  }

  public void generateMonthlyReport(int month) throws SQLException, IOException {
    List<String> salesData = month > 0 && month <= 12
        ? salesRepository.getSalesDataForMonth(month)
        : salesRepository.getAllSalesData();

    String reportContent = String.join("\n", salesData);
    String filename = "report_" + month + ".csv";
    reportGenerator.generateReport(filename, reportContent);
  }
}

public class PriceCalculator {
  private static final double FIRST_TIER_DISCOUNT_RATE = 0.85;
  private static final double SECOND_TIER_DISCOUNT_RATE = 0.75;
  private static final int FIRST_TIER_THRESHOLD = 500;
  private static final int SECOND_TIER_THRESHOLD = 1000;

  public int calculateFinalPrice(int baseAmount, int multiplier, int additionalCost) {
    int subtotal = baseAmount * multiplier + additionalCost;

    if (subtotal > SECOND_TIER_THRESHOLD) {
      return (int) (subtotal * FIRST_TIER_DISCOUNT_RATE * SECOND_TIER_DISCOUNT_RATE);
    }
    if (subtotal > FIRST_TIER_THRESHOLD) {
      return (int) (subtotal * FIRST_TIER_DISCOUNT_RATE);
    }
    return subtotal;
  }
}