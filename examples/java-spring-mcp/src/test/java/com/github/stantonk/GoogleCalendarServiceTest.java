package com.github.stantonk;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class GoogleCalendarServiceTest {

    @Test
    public void testGoogleCalendarServiceInitialization() {
        // This test verifies that the service throws the expected exception when Descope client is not configured
        assertThrows(com.descope.exception.ClientSetupException.class, () -> {
            new GoogleCalendarService();
        });
    }

    @Test
    public void testGetUpcomingEventsWithoutEnvironmentVariables() {
        // This test verifies that the service throws the expected exception when Descope client is not configured
        assertThrows(com.descope.exception.ClientSetupException.class, () -> {
            GoogleCalendarService service = new GoogleCalendarService();
            service.getUpcomingEvents("demo_token", "demo_user", 10);
        });
    }

    @Test
    public void testGetEventsForDateRangeWithoutEnvironmentVariables() {
        // This test verifies that the service throws the expected exception when Descope client is not configured
        assertThrows(com.descope.exception.ClientSetupException.class, () -> {
            GoogleCalendarService service = new GoogleCalendarService();
            service.getEventsForDateRange("demo_token", "demo_user", "2024-01-01", "2024-01-31");
        });
    }

    @Test
    public void testSearchEventsWithoutEnvironmentVariables() {
        // This test verifies that the service throws the expected exception when Descope client is not configured
        assertThrows(com.descope.exception.ClientSetupException.class, () -> {
            GoogleCalendarService service = new GoogleCalendarService();
            service.searchEvents("demo_token", "demo_user", "meeting");
        });
    }

    @Test
    public void testCreateEventWithoutEnvironmentVariables() {
        // This test verifies that the service throws the expected exception when Descope client is not configured
        assertThrows(com.descope.exception.ClientSetupException.class, () -> {
            GoogleCalendarService service = new GoogleCalendarService();
            String eventData = "{\"summary\":\"Test Event\",\"start\":{\"dateTime\":\"2024-01-01T10:00:00Z\"},\"end\":{\"dateTime\":\"2024-01-01T11:00:00Z\"}}";
            service.createEvent("demo_token", "demo_user", eventData);
        });
    }
}
