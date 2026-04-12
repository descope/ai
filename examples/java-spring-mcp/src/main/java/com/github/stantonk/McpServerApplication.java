package com.github.stantonk;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

/**
 * Spring Boot application for the MCP server with OAuth2 security.
 * This application integrates Spring Security OAuth2 with the MCP server.
 */
@SpringBootApplication
@ComponentScan(basePackages = "com.github.stantonk")
public class McpServerApplication {

    public static void main(String[] args) {
        // Initialize Spring Boot application
        SpringApplication.run(McpServerApplication.class, args);
        
        // Start the MCP server
        App.main(args);
    }
}
