CREATE TABLE `gozupees_phonenumbers` (
  `Id` int(11) NOT NULL AUTO_INCREMENT,
  `PhoneNumber` varchar(20) DEFAULT NULL,
  `IncomingSIPTrunkID` int(11) DEFAULT NULL,
  `OutgoingSIPTrunkID` int(11) DEFAULT NULL,
  `FallbackSIPTrunkID` int(11) DEFAULT NULL,
  `FallbackPhoneNumber` varchar(20) DEFAULT NULL,
  `Status` enum('Active','Suspended','Ported') NOT NULL,
  `CreatedAt` timestamp NULL DEFAULT current_timestamp(),
  `UpdatedAt` timestamp NULL DEFAULT current_timestamp(),
  `Description` varchar(50) DEFAULT '',
  `PortedMarkedAt` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`Id`),
  UNIQUE KEY `PhoneNumber` (`PhoneNumber`),
  UNIQUE KEY `idx_phonenumber` (`PhoneNumber`),
  KEY `idx_status` (`Status`)
);

SET GLOBAL event_scheduler = ON;
DROP EVENT IF EXISTS ported_numbers_cleanup;
DELIMITER $$
CREATE EVENT ported_numbers_cleanup
    ON SCHEDULE EVERY 1 MINUTE STARTS '2025-01-01 00:00:00'
    DO
    BEGIN
        DELETE FROM gozupees_phonenumbers WHERE Status='Ported' AND DATE_ADD(PortedMarkedAt, INTERVAL 30 MINUTE) < CURRENT_TIMESTAMP;
    END$$
DELIMITER ;
