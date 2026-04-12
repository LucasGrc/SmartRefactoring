package examples;

import java.sql.Connection;
import java.sql.SQLException;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import java.util.HashMap;
import java.util.function.Runnable;

interface Worker {
    void work();
}

interface Maintainer {
    void maintainServers();
}

interface Shape {
    int calculateArea();
}

class Rectangle implements Shape {
    protected final int width;
    protected final int height;
    
    public Rectangle(int width, int height) {
        this.width = width;
        this.height = height;
    }
    
    public int getWidth() {
        return width;
    }
    
    public int getHeight() {
        return height;
    }
    
    @Override
    public int calculateArea() {
        return width * height;
    }
}

class Square implements Shape {
    private final int side;
    
    public Square(int side) {
        this.side = side;
    }
    
    public int getSide() {
        return side;
    }
    
    @Override
    public int calculateArea() {
        return side * side;
    }
}

interface DatabaseService {
    void saveResult(int value) throws SQLException;
}

interface FileService {
    void writeResult(int value, Path filePath) throws IOException;
}

interface TypeProcessor {
    void processType();
}

class TypeOneProcessor implements TypeProcessor {
    @Override
    public void processType() {
        System.out.println("type 1");
    }
}

class TypeTwoProcessor implements TypeProcessor {
    @Override
    public void processType() {
        System.out.println("type 2");
    }
}

class TypeThreeProcessor implements TypeProcessor {
    @Override
    public void processType() {
        System.out.println("type 3");
    }
}

class DefaultTypeProcessor implements TypeProcessor {
    @Override
    public void processType() {
        System.out.println("other");
    }
}

class ProcessorFactory {
    private static final Map<Integer, TypeProcessor> processors = new HashMap<>();
    
    static {
        processors.put(1, new TypeOneProcessor());
        processors.put(2, new TypeTwoProcessor());
        processors.put(3, new TypeThreeProcessor());
    }
    
    public static TypeProcessor createProcessor(int type) {
        return processors.getOrDefault(type, new DefaultTypeProcessor());
    }
}

class DataProcessor {
    private static final int THRESHOLD_VALUE = 42;
    private static final int RETRY_COUNT = 3;
    
    private final DatabaseService databaseService;
    private final FileService fileService;
    
    public DataProcessor(DatabaseService databaseService, FileService fileService) {
        this.databaseService = databaseService;
        this.fileService = fileService;
    }
    
    public void processAndSaveData(int firstValue, int secondValue, boolean shouldProcess, Path outputPath) {
        if (!shouldProcess) {
            return;
        }
        
        int result = multiplyValues(firstValue, secondValue);
        
        if (result <= THRESHOLD_VALUE) {
            return;
        }
        
        saveDataWithRetry(result, outputPath);
    }
    
    private int multiplyValues(int firstValue, int secondValue) {
        return firstValue * secondValue;
    }
    
    private void saveDataWithRetry(int result, Path outputPath) {
        for (int attempt = 0; attempt < RETRY_COUNT; attempt++) {
            try {
                saveData(result, outputPath);
                return;
            } catch (SQLException | IOException e) {
                System.err.println("Attempt " + (attempt + 1) + " failed: " + e.getMessage());
                if (attempt == RETRY_COUNT - 1) {
                    throw new RuntimeException("Failed to save data after " + RETRY_COUNT + " attempts", e);
                }
            }
        }
    }
    
    private void saveData(int result, Path outputPath) throws SQLException, IOException {
        databaseService.saveResult(result);
        fileService.writeResult(result, outputPath);
    }
}

public class BadCode implements Worker, Maintainer {
    private final int type;
    private String dataContent;
    private final TypeProcessor typeProcessor;
    private final DataProcessor dataProcessor;
    
    public BadCode(int type, DataProcessor dataProcessor) {
        this.type = type;
        this.typeProcessor = ProcessorFactory.createProcessor(type);
        this.dataProcessor = dataProcessor;
    }
    
    public void setDataContent(String dataContent) {
        this.dataContent = dataContent;
    }
    
    public String getDataContent() {
        return dataContent;
    }
    
    public void executeTypeSpecificLogic() {
        typeProcessor.processType();
    }
    
    public void processAndSaveData(int firstValue, int secondValue, boolean shouldProcess, Path outputPath) {
        dataProcessor.processAndSaveData(firstValue, secondValue, shouldProcess, outputPath);
    }
    
    @Override
    public void work() {
        System.out.println("working");
    }
    
    @Override
    public void maintainServers() {
        System.out.println("maintaining");
    }
}